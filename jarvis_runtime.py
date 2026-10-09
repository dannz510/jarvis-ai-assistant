"""OpenJarvis runtime bridge for the desktop assistant."""

import os
import threading
import time
from pathlib import Path
from branding import ASSISTANT_NAME, OWNER_NAME, SYSTEM_PROMPT_PREFIX
from Brain.conversation_context import ConversationContext
from Brain.agent_state import AgentState, AgentStateMachine, EventBus
from Brain.model_router import ModelRouter
from Brain.tool_registry import create_default_registry
from Brain.local_tool_router import LocalToolRouter
from Brain.task_store import TaskStore
from Brain.settings import default_settings_path
from Brain.logger import logger
from Brain.agent_loop import ReActAgent

# Use the fast 1.5B model by default for quick responses (~3-8s cold, <2s warm).
# Override with ASTRA_MODEL=qwen2.5-coder:7b-instruct for full reasoning if you have GPU.
DEFAULT_MODEL = os.environ.get("ASTRA_MODEL", "qwen2.5:1.5b")
DEFAULT_AGENT = "simple"
VALID_AGENTS = {"simple", "native_react", "orchestrator", "agentic"}
# Safe default tools - file_write and file_list are opt-in for security
DEFAULT_TOOLS = ["calculator", "web_search", "think"]
# ASTRA_MAX_TOKENS controls the maximum tokens per LLM response.
# Default: 768 -- enough for substantive answers, summaries, and code snippets.
_DEFAULT_MAX_TOKENS = 768
try:
    _MAX_TOKENS = int(os.environ.get("ASTRA_MAX_TOKENS", str(_DEFAULT_MAX_TOKENS)))
except (TypeError, ValueError):
    _MAX_TOKENS = _DEFAULT_MAX_TOKENS

# Hard deadline: 30 seconds max for any request. Override with ASTRA_REQUEST_TIMEOUT.
try:
    REQUEST_DEADLINE_SECONDS = int(os.environ.get("ASTRA_REQUEST_TIMEOUT", "30"))
except (TypeError, ValueError):
    REQUEST_DEADLINE_SECONDS = 30


class AstraRuntime:
    def __init__(self):
        self._lock = threading.RLock()
        self._clients = {}
        self.context = ConversationContext(max_turns=8)
        self.event_bus = EventBus()
        self.state_machine = AgentStateMachine(self.event_bus)
        self.model_router = ModelRouter()
        self.tool_registry = create_default_registry()
        self.local_tool_router = LocalToolRouter(self.tool_registry)
        self._memory = None
        self._tasks = None
        self.memory_enabled = os.environ.get("ASTRA_MEMORY_ENABLED", "1").strip().casefold() not in {"0", "false", "no", "off"}
        self.memory_policy = os.environ.get("ASTRA_MEMORY_POLICY", "explicit").strip().casefold()
        self._pending_memory_text = None
        self._request_lock = threading.Lock()
        self._agent_step_callback = None
        self._agentic_model = os.environ.get("ASTRA_AGENTIC_MODEL", "qwen2.5:1.5b")

    def _memory_store(self, include_disabled=False):
        if not self.memory_enabled and not include_disabled:
            return None
        if self._memory is None:
            try:
                from openjarvis.core.paths import get_config_dir
                from Brain.memory_store import MemoryStore

                self._memory = MemoryStore(Path(get_config_dir()) / "ASTRA_MEMORY.sqlite3")
            except Exception:
                return None
        self._memory.memory_policy = self.memory_policy
        return self._memory

    def _task_store(self):
        if self._tasks is None:
            path = Path(os.environ.get(
                "ASTRA_TASK_DATABASE",
                str(default_settings_path().with_name("ASTRA_TASKS.sqlite3")),
            ))
            try:
                self._tasks = TaskStore(path)
                latest = self._tasks.latest()
                if latest and time.time() - latest["updated_at"] < 86400:
                    self.context.restore_working(
                        active_app=latest.get("active_application"),
                        active_file=latest.get("active_file"),
                        active_task=latest.get("goal"),
                    )
            except Exception:
                self._tasks = False
        return self._tasks or None

    def list_recent_tasks(self, limit=50):
        store = self._task_store()
        return store.list_recent(limit) if store else []

    def set_memory_enabled(self, enabled):
        self.memory_enabled = bool(enabled)

    def set_memory_policy(self, policy):
        policy = str(policy).casefold().strip()
        if policy not in {"explicit", "ask", "do_not_save"}:
            raise ValueError("Memory policy must be explicit, ask, or do_not_save.")
        self.memory_policy = policy
        if self._memory is not None:
            self._memory.memory_policy = policy

    def list_memories(self):
        store = self._memory_store(include_disabled=True)
        return store.list_memories() if store else []

    def delete_memory(self, memory_id):
        store = self._memory_store(include_disabled=True)
        return store.delete(memory_id) if store else False

    def pin_memory(self, memory_id, pinned=True):
        store = self._memory_store(include_disabled=True)
        return store.set_pinned(memory_id, pinned) if store else False

    def clear_memories(self):
        store = self._memory_store(include_disabled=True)
        if store:
            store.clear()

    def _client_for(self, model):
        client = self._clients.get(model)
        if client is None:
            from openjarvis import Jarvis

            client = Jarvis(engine_key="ollama", model=model)
            client.config.agent.context_from_memory = False
            client.config.agent.default_system_prompt = SYSTEM_PROMPT_PREFIX
            self._clients[model] = client
        return client

    def list_models(self):
        with self._lock:
            models = self._client_for(DEFAULT_MODEL).list_models()
            self.model_router.set_available_models(models)
            return models

    def ask_full(self, prompt, model=None, agent=DEFAULT_AGENT, tools=None):
        logger.info(f"Incoming request: {prompt[:100]}")
        model_choice = self.model_router.route(prompt, explicit_model=model)
        model = model_choice.model
        logger.debug(f"Routed to model: {model} (Tier: {model_choice.tier}, Reason: {model_choice.reason})")
        if not self._request_lock.acquire(blocking=False):
            logger.warning("Request rejected: Agent is busy.")
            return {"content": "A previous request is still processing. Please wait a moment.", "error": "busy"}

        completed = threading.Event()
        outcome = {}

        confirmation_result = self._resolve_memory_confirmation(prompt)
        if confirmation_result is not None:
            self._request_lock.release()
            completed.set()
            return confirmation_result

        def run_request():
            task_id = None
            task_store = self._task_store()
            try:
                self.state_machine.transition(AgentState.PROCESSING, "Request accepted")
                self.state_machine.transition(
                    AgentState.THINKING,
                    f"{model_choice.tier} model: {model_choice.reason}",
                )
                if agent == "agentic":
                    return self._run_agentic(prompt, model, task_store, task_id, outcome)
                active_tools = tools if tools is not None else DEFAULT_TOOLS
                if active_tools or self.local_tool_router.route(prompt):
                    self.state_machine.transition(AgentState.TOOL_SELECTION, "Selecting from enabled tools")
                with self._lock:
                    route = self.local_tool_router.route(prompt)
                    follow_up = self.context.is_follow_up(prompt) or bool(
                        route and route[0] == "__confirmation__"
                    )
                    self.context.add_user(prompt)
                    if task_store:
                        task_id = task_store.begin(
                            prompt,
                            follow_up=follow_up,
                            active_application=self.context.working.active_app,
                            active_file=self.context.working.active_file,
                        )
                    local_result = self.local_tool_router.execute(prompt)
                    if local_result is not None:
                        outcome["result"] = local_result
                        tool_data = local_result.get("tool_results", [{}])[0].get("result", {})
                        if tool_data.get("confirmation_required"):
                            if task_store:
                                task_store.observe(task_id, "Waiting for explicit confirmation.", "Waiting for confirmation")
                            self.state_machine.transition(
                                AgentState.WAITING_FOR_CLARIFICATION,
                                "Waiting for confirmation before changing a file",
                            )
                        else:
                            self.state_machine.transition(AgentState.EXECUTING, "Running a scoped local file tool")
                            self.state_machine.transition(AgentState.OBSERVING, "Checking local tool result")
                            if task_store:
                                completed_tool = local_result.get("tool_results", [{}])[0].get("tool_name", "")
                                observation = (
                                    "UI Automation operation completed."
                                    if completed_tool in {"windows_list", "window_inspect", "window_focus",
                                                          "ui_control_click", "ui_control_set_text"}
                                    else local_result.get("content", "")
                                )
                                task_store.complete_step(task_id, prompt, observation)
                                artifact_tools = {
                                    "file_create", "file_copy", "file_move", "office_word_create",
                                    "office_word_append", "office_excel_create", "office_excel_chart",
                                    "office_ppt_create",
                                }
                                if completed_tool in artifact_tools:
                                    payload = tool_data.get("result", tool_data) if isinstance(tool_data, dict) else tool_data
                                    if isinstance(payload, dict):
                                        artifact = payload.get("path") or payload.get("target") or payload.get("destination")
                                    else:
                                        artifact = payload
                                    if artifact:
                                        task_store.add_artifact(task_id, artifact)
                                task_store.finish(task_id, "completed")
                        self.context.add_assistant(local_result.get("content", ""))
                        self.state_machine.transition(AgentState.RESPONDING, "Preparing ASTRA response")
                        self.state_machine.transition(AgentState.COMPLETED, "Local tool request completed")
                        return
                    client = self._client_for(model)
                    recent_turns = self.context.recent_turns(4)
                    context = "\n".join(
                        f"{speaker}: {content[:500]}" for speaker, content in recent_turns
                    )
                    working_context = self.context.context_for(prompt)
                    memory_context = ""
                    memory_store = self._memory_store()
                    if memory_store:
                        memories = memory_store.retrieve(prompt, limit=3)
                        if memories:
                            memory_context = "\n".join(
                                f"- [{item['category']}] {item['text']}" for item in memories
                            )
                    context_blocks = [
                        block for block in (context, working_context, memory_context) if block
                    ]
                    request = (
                        f"{SYSTEM_PROMPT_PREFIX}\n\n"
                        f"Working context:\n{working_context}\n\n"
                        f"Relevant persistent memories:\n{memory_context}\n\n"
                        f"Recent conversation:\n{context}\n\nCurrent request:\n{prompt}"
                        if context_blocks else
                        f"{SYSTEM_PROMPT_PREFIX}\n\n{prompt}"
                    )
                    outcome["result"] = client.ask_full(
                        request,
                        model=model,
                        agent=agent,
                        tools=active_tools,
                        temperature=0.2,
                        max_tokens=_MAX_TOKENS,
                        context=False,
                    )
                    answer = outcome["result"].get("content", "")
                    tool_results = outcome["result"].get("tool_results", [])
                    if tool_results:
                        self.state_machine.transition(
                            AgentState.EXECUTING,
                            f"{len(tool_results)} tool call(s) returned",
                        )
                        self.state_machine.transition(AgentState.OBSERVING, "Reviewing tool results")
                    if task_store:
                        task_store.complete_step(task_id, prompt, answer)
                        for tool_result in tool_results:
                            raw_result = tool_result.get("result")
                            if isinstance(raw_result, dict):
                                for key in ("path", "target", "destination"):
                                    if raw_result.get(key):
                                        task_store.add_artifact(task_id, raw_result[key])
                        task_store.finish(task_id, "completed")
                    self.context.add_assistant(answer)
                    if memory_store:
                        memory_store.maybe_store_important_turn(prompt, answer)
                        if (self.memory_policy == "ask" and
                                memory_store.requires_confirmation(prompt)):
                            self._pending_memory_text = prompt
                            confirmation = (
                                "\n\nBạn có muốn ASTRA lưu thông tin này vào bộ nhớ không? Hãy trả lời có hoặc không."
                                if any(marker in prompt.casefold() for marker in ("tôi", "hãy", "nhớ", "lưu"))
                                else "\n\nWould you like ASTRA to save this to memory? Reply yes or no."
                            )
                            answer += confirmation
                            outcome["result"]["content"] = answer
                    self.state_machine.transition(AgentState.RESPONDING, "Preparing ASTRA response")
                    self.state_machine.transition(AgentState.COMPLETED, "Request completed")
                    logger.info("Request processing completed successfully.")
            except Exception as exc:
                logger.error(f"Error processing request: {exc}", exc_info=True)
                outcome["error"] = str(exc)
                try:
                    store = self._task_store()
                    if store:
                        store.add_error(task_id, exc)
                except Exception:
                    pass
                try:
                    if self.state_machine.state != AgentState.ERROR:
                        self.state_machine.transition(AgentState.ERROR, str(exc))
                except ValueError:
                    pass
            finally:
                completed.set()
                self._request_lock.release()

        threading.Thread(target=run_request, name="astra-inference", daemon=True).start()
        if not completed.wait(REQUEST_DEADLINE_SECONDS):
            logger.error(f"Request timeout after {REQUEST_DEADLINE_SECONDS}s")
            return {
                "content": (
                    f"The model did not respond within {REQUEST_DEADLINE_SECONDS}s. "
                    "Try a shorter question, reduce ASTRA_MAX_TOKENS, or check that Ollama is running."
                ),
                "error": "timeout",
            }
        if "error" in outcome:
            logger.error(f"Local model error: {outcome['error']}")
            return {"content": f"Local model error: {outcome['error']}", "error": outcome["error"]}
        return outcome["result"]

    def _resolve_memory_confirmation(self, prompt):
        if not self._pending_memory_text:
            return None
        answer = str(prompt or "").strip().casefold().rstrip(".!?")
        affirmative = {"yes", "yes save", "please save", "có", "có lưu", "hãy lưu", "lưu đi", "đồng ý"}
        negative = {"no", "no thanks", "don't save", "do not save", "không", "không lưu", "hủy"}
        if answer not in affirmative | negative:
            self._pending_memory_text = None
            return None

        remembered_text = self._pending_memory_text
        self._pending_memory_text = None
        if answer in affirmative:
            store = self._memory_store()
            saved = bool(store and store.add(
                remembered_text, category="semantic", importance=5, source="explicit_turn"
            ))
            response = "Đã lưu vào bộ nhớ của ASTRA." if answer in {"có", "có lưu", "hãy lưu", "lưu đi", "đồng ý"} else "Saved to ASTRA's memory."
            if not saved:
                response = "Bộ nhớ đang tắt hoặc thông tin không thể lưu an toàn." if answer in {"có", "có lưu", "hãy lưu", "lưu đi", "đồng ý"} else "Memory is disabled or this information could not be saved safely."
            tool_result = {"tool_name": "memory_manage", "success": saved}
        else:
            response = "ASTRA sẽ không lưu thông tin đó." if answer in {"không", "không lưu", "hủy"} else "ASTRA will not save that information."
            tool_result = {"tool_name": "memory_manage", "success": True}

        try:
            self.state_machine.transition(AgentState.PROCESSING, "Resolving memory preference")
            self.state_machine.transition(AgentState.THINKING, "Applying memory policy")
            self.state_machine.transition(AgentState.RESPONDING, response)
            self.state_machine.transition(AgentState.COMPLETED, "Memory preference applied")
        except ValueError:
            pass
        self.context.add_user(prompt)
        self.context.add_assistant(response)
        return {"content": response, "engine": "astra_memory", "model": "local", "tool_results": [tool_result]}

    def set_agent_step_callback(self, callback):
        self._agent_step_callback = callback

    def _run_agentic(self, prompt, model, task_store, task_id, outcome):
        """Run the goal through the ReAct agent loop and capture the summary."""
        state_machine = self.state_machine

        def on_step(event):
            try:
                event_type = event.get("type")
                if event_type == "thinking":
                    state_machine.transition(AgentState.THINKING, "Agent reasoning")
                elif event_type == "step":
                    state_machine.transition(
                        AgentState.TOOL_SELECTION,
                        f"Agent selected tool: {event.get('action')}",
                    )
                elif event_type == "observation":
                    state_machine.transition(
                        AgentState.OBSERVING,
                        f"Tool result: {str(event.get('observation'))[:120]}",
                    )
                elif event_type == "error":
                    state_machine.transition(AgentState.ERROR, str(event.get("error")))
            except ValueError:
                pass
            if self._agent_step_callback is not None:
                try:
                    self._agent_step_callback(event)
                except Exception:
                    logger.debug("Agent step callback failed", exc_info=True)

        agent = ReActAgent(model=self._agentic_model, on_step=on_step)
        # Warm up agentic model on first use
        if not hasattr(self, '_agentic_warmed_up'):
            self.warm_model(self._agentic_model)
            self._agentic_warmed_up = True
        summary = agent.run(prompt)
        if task_store and task_id:
            task_store.complete_step(task_id, prompt, summary)
            task_store.finish(task_id, "completed")
        outcome["result"] = {
            "content": summary,
            "engine": "astra_react",
            "model": model,
            "tool_results": [],
        }

    def warm_model(self, model=None):
        """Load the selected Ollama model in the background and keep it resident."""
        model = model or DEFAULT_MODEL
        try:
            import ollama
            # Warm up with a tiny prompt to load model into VRAM/RAM
            ollama.generate(model=model, prompt=" ", keep_alive="30m",
                            options={"num_ctx": 2048, "num_predict": 1, "temperature": 0})
            # Pre-warm with a real prompt for JIT compilation
            ollama.generate(model=model, prompt="Hello", keep_alive="30m",
                            options={"num_ctx": 2048, "num_predict": 5, "temperature": 0.1})
            return True
        except Exception as exc:
            return str(exc)

    def read_memory(self):
        from openjarvis.core.paths import get_config_dir

        memory_path = Path(get_config_dir()) / "MEMORY.md"
        if not memory_path.exists():
            return memory_path, ""
        return memory_path, memory_path.read_text(encoding="utf-8")

    def add_memory(self, entry):
        from openjarvis.core.paths import get_config_dir

        memory_path = Path(get_config_dir()) / "MEMORY.md"
        memory_path.parent.mkdir(parents=True, exist_ok=True)
        existing = memory_path.read_text(encoding="utf-8") if memory_path.exists() else ""
        memory_path.write_text(existing.rstrip() + f"\n- {entry.strip()}\n", encoding="utf-8")
        memory_store = self._memory_store(include_disabled=True)
        if memory_store:
            memory_store.add(entry, category="semantic", importance=4, source="memory_editor")
        return memory_path

    def write_memory(self, content):
        from openjarvis.core.paths import get_config_dir

        memory_path = Path(get_config_dir()) / "MEMORY.md"
        memory_path.parent.mkdir(parents=True, exist_ok=True)
        normalized = content.rstrip()
        memory_path.write_text(f"{normalized}\n" if normalized else "", encoding="utf-8")
        memory_store = self._memory_store(include_disabled=True)
        if memory_store:
            memory_store.replace_profile(normalized)
        return memory_path

    def close(self):
        with self._lock:
            for client in self._clients.values():
                client.close()
            self._clients.clear()


_runtime = AstraRuntime()


def get_runtime():
    return _runtime
