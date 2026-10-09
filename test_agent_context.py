"""Unit coverage for ASTRA's state and short-term context foundations."""

import unittest
import tempfile
from unittest.mock import patch
from pathlib import Path

from Brain.agent_state import AgentState, AgentStateMachine, EventBus
from Brain.conversation_context import ConversationContext
from Brain.memory_store import MemoryStore
from Brain.model_router import ModelRouter
from Brain.local_tool_router import LocalToolRouter
from Brain.speech_turn import SpeechTurnBuffer
from Brain.voice_activity import VoiceActivityDetector
from Brain.task_store import TaskStore
from Brain.settings import SettingsStore
from Brain.tool_registry import create_default_registry
from jarvis_runtime import AstraRuntime
from Vision import Vbrain


class AgentStateTests(unittest.TestCase):
    def test_state_transitions_publish_events(self):
        events = []
        bus = EventBus()
        bus.subscribe(events.append)
        machine = AgentStateMachine(bus)

        machine.transition(AgentState.PROCESSING, "accepted")
        machine.transition(AgentState.THINKING)

        self.assertEqual(machine.state, AgentState.THINKING)
        self.assertEqual([event.state for event in events], [AgentState.PROCESSING, AgentState.THINKING])

    def test_invalid_state_transition_is_rejected(self):
        machine = AgentStateMachine()
        with self.assertRaises(ValueError):
            machine.transition(AgentState.EXECUTING)


class ConversationContextTests(unittest.TestCase):
    def test_follow_up_keeps_active_application_context(self):
        context = ConversationContext()
        context.add_user("Mở Excel")
        context.add_assistant("Đã mở Excel.")
        context.add_user("Tạo biểu đồ cho bảng này")

        working_context = context.context_for("Tạo biểu đồ cho bảng này")
        self.assertIn("Microsoft Excel", working_context)
        self.assertEqual(context.recent_turns()[-1], ("User", "Tạo biểu đồ cho bảng này"))

    def test_turn_history_is_bounded(self):
        context = ConversationContext(max_turns=2)
        for item in ("one", "two", "three"):
            context.add_user(item)

        self.assertEqual(len(context.recent_turns()), 2)
        self.assertEqual(context.recent_turns()[0], ("User", "two"))

    def test_follow_up_detection_preserves_app_task_without_matching_copula_it(self):
        context = ConversationContext()
        context.add_user("Open Excel")

        self.assertTrue(context.is_follow_up("Create a chart"))
        self.assertFalse(context.is_follow_up("What time is it in Bangkok?"))
        self.assertFalse(context.is_follow_up("Open Word"))


class TaskStoreTests(unittest.TestCase):
    def test_task_state_persists_steps_context_and_artifacts(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "tasks.sqlite3"
            tasks = TaskStore(path)
            task_id = tasks.begin(
                "Analyze the sales workbook",
                active_application="Microsoft Excel",
                active_file="sales.xlsx",
            )
            tasks.complete_step(task_id, "Analyze the sales workbook", "Summary completed")
            tasks.add_artifact(task_id, "sales_summary.xlsx")
            tasks.finish(task_id, "completed")

            restored = TaskStore(path).latest()

        self.assertEqual(restored["task_id"], task_id)
        self.assertEqual(restored["active_application"], "Microsoft Excel")
        self.assertEqual(restored["active_file"], "sales.xlsx")
        self.assertEqual(restored["completed_steps"][0]["result"], "Summary completed")
        self.assertEqual(restored["artifacts"], ["sales_summary.xlsx"])

    def test_task_store_rejects_sensitive_goal_and_error_text(self):
        with tempfile.TemporaryDirectory() as directory:
            tasks = TaskStore(Path(directory) / "tasks.sqlite3")
            self.assertIsNone(tasks.begin("Remember my password is hunter2"))
            self.assertIsNone(tasks.begin('set text in control "Password" in window "Login" to "secret"'))
            task_id = tasks.begin("Open my spreadsheet")

            self.assertFalse(tasks.add_error(task_id, "API key: abcdefghijklmnop"))
            self.assertEqual(tasks.latest()["errors"], [])

    def test_runtime_restores_task_context_after_restart(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "tasks.sqlite3"
            tasks = TaskStore(path)
            tasks.begin("Open Excel", active_application="Microsoft Excel", active_file="sales.xlsx")

            runtime = AstraRuntime()
            with patch.dict("os.environ", {"ASTRA_TASK_DATABASE": str(path)}):
                runtime._task_store()

        self.assertEqual(runtime.context.working.active_app, "Microsoft Excel")
        self.assertEqual(runtime.context.working.active_file, "sales.xlsx")

    def test_runtime_persists_completed_model_task(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(
            "os.environ", {"ASTRA_TASK_DATABASE": str(Path(directory) / "tasks.sqlite3")}
        ):
            runtime = AstraRuntime()

            class FakeClient:
                def ask_full(self, _prompt, **_kwargs):
                    return {"content": "Summary ready.", "tool_results": [], "engine": "fake", "model": "fake"}

            runtime._client_for = lambda _model: FakeClient()
            result = runtime.ask_full("Summarize this article", tools=[])
            task = runtime._task_store().latest()

        self.assertEqual(result["content"], "Summary ready.")
        self.assertEqual(task["goal"], "Summarize this article")
        self.assertEqual(task["status"], "completed")
        self.assertEqual(task["completed_steps"][0]["result"], "Summary ready.")

    def test_runtime_injects_active_application_into_follow_up(self):
        prompts = []

        class FakeClient:
            def ask_full(self, prompt, **_kwargs):
                prompts.append(prompt)
                return {"content": "Done", "tool_results": [], "engine": "fake", "model": "fake"}

        runtime = AstraRuntime()
        runtime._client_for = lambda _model: FakeClient()
        runtime.ask_full("I want to open Excel and discuss this", tools=[])
        runtime.ask_full("Tạo biểu đồ cho bảng này", tools=[])

        self.assertIn("Current application: Microsoft Excel.", prompts[1])


class MemoryStoreTests(unittest.TestCase):
    def test_retrieval_is_relevant_and_sensitive_values_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            memory = MemoryStore(Path(directory) / "memory.sqlite3", embedding_model=None)
            memory.add("Dannz prefers Vietnamese replies", category="semantic", importance=5)
            memory.add("The laptop battery was replaced in June", category="episodic", importance=2)

            matches = memory.retrieve("Vietnamese reply preference")
            self.assertEqual(matches[0]["text"], "Dannz prefers Vietnamese replies")
            self.assertEqual(memory.retrieve("weekly sales report"), [])
            self.assertIsNone(memory.add("My password is secret-value"))
            self.assertIsNone(memory.add("Remember my email is dannz@example.com"))
            self.assertIsNone(memory.add("My phone number is +1 555 123 4567"))

    def test_ask_policy_requires_confirmation_before_persisting(self):
        with tempfile.TemporaryDirectory() as directory:
            memory = MemoryStore(Path(directory) / "memory.sqlite3", embedding_model=None)
            memory.memory_policy = "ask"
            runtime = AstraRuntime()
            runtime._memory = memory
            runtime.memory_policy = "ask"

            class FakeClient:
                def ask_full(self, _prompt, **_kwargs):
                    return {"content": "Understood.", "tool_results": [], "engine": "fake", "model": "fake"}

            runtime._client_for = lambda _model: FakeClient()
            result = runtime.ask_full("Remember that I prefer concise answers", tools=[])
            self.assertIn("Reply yes or no", result["content"])
            self.assertEqual(memory.list_memories(), [])

            saved = runtime.ask_full("yes", tools=[])
            self.assertIn("Saved", saved["content"])
            self.assertEqual(len(memory.list_memories()), 1)

    def test_profile_replacement_removes_previous_editor_entries(self):
        with tempfile.TemporaryDirectory() as directory:
            memory = MemoryStore(Path(directory) / "memory.sqlite3", embedding_model=None)
            memory.replace_profile("- Old preference")
            memory.replace_profile("- Preferred language: Vietnamese")

            saved = [item["text"] for item in memory.list_memories()]
            self.assertEqual(saved, ["Preferred language: Vietnamese"])


class SpeechTurnTests(unittest.TestCase):
    def test_incomplete_clause_waits_and_combines_next_segment(self):
        buffer = SpeechTurnBuffer(normal_timeout=0.5, incomplete_timeout=2.0)
        buffer.add_final("what time is it in", now=1.0)

        self.assertFalse(buffer.should_finalize(2.0))
        buffer.add_final("Bangkok", now=2.1)
        self.assertFalse(buffer.should_finalize(2.4))
        self.assertTrue(buffer.should_finalize(2.7))
        self.assertEqual(buffer.consume(), "what time is it in Bangkok")

    def test_partial_transcript_never_finalizes_a_turn(self):
        buffer = SpeechTurnBuffer(normal_timeout=0.1)
        buffer.add_final("open excel", now=1.0)
        buffer.update_partial("open excel and create")

        self.assertFalse(buffer.should_finalize(5.0))
        self.assertEqual(buffer.preview, "open excel and create")

    def test_active_speech_blocks_turn_finalization(self):
        buffer = SpeechTurnBuffer(normal_timeout=0.5)
        buffer.add_final("open excel", now=1.0)

        self.assertFalse(buffer.should_finalize(3.0, speech_active=True))
        self.assertTrue(buffer.should_finalize(3.0, speech_active=False))


class VoiceActivityTests(unittest.TestCase):
    def test_webrtc_frames_use_hangover_to_keep_short_pauses_active(self):
        class FakeVAD:
            def __init__(self):
                self.frame_lengths = []

            def is_speech(self, frame, sample_rate):
                self.frame_lengths.append((len(frame), sample_rate))
                return len(self.frame_lengths) <= 3

        vad_engine = FakeVAD()
        detector = VoiceActivityDetector(vad_engine=vad_engine, hangover_seconds=0.45)
        self.assertTrue(detector.process(b"\x00" * 4096, now=1.0))
        self.assertTrue(all(size == 640 and rate == 16000 for size, rate in vad_engine.frame_lengths))
        self.assertTrue(detector.process(b"\x00" * 4096, now=1.3))
        self.assertFalse(detector.process(b"\x00" * 4096, now=1.6))

    def test_invalid_webrtc_frame_falls_back_to_rms_detection(self):
        class BrokenVAD:
            def is_speech(self, _frame, _sample_rate):
                raise ValueError("unsupported frame")

        detector = VoiceActivityDetector(vad_engine=BrokenVAD())
        speech = bytearray()
        for _ in range(2048):
            speech.extend((2500).to_bytes(2, "little", signed=True))

        self.assertTrue(detector.process(speech, now=1.0))
        self.assertFalse(detector.using_webrtc)


class VisionTests(unittest.TestCase):
    def test_vision_request_uses_local_ollama_multimodal_payload(self):
        response = type("Response", (), {
            "raise_for_status": lambda self: None,
            "json": lambda self: {"message": {"content": "A receipt."}},
        })()
        with patch.object(Vbrain.requests, "post", return_value=response) as post:
            answer = Vbrain.vision_brain("encoded-image", prompt="Read the receipt", model="vision-test")

        self.assertEqual(answer, "A receipt.")
        args, kwargs = post.call_args
        self.assertTrue(args[0].endswith("/api/chat"))
        self.assertEqual(kwargs["json"]["model"], "vision-test")
        self.assertEqual(kwargs["json"]["messages"][0]["content"], "Read the receipt")
        self.assertEqual(kwargs["json"]["messages"][0]["images"], ["encoded-image"])

    def test_empty_vision_image_is_rejected_before_network_call(self):
        with patch.object(Vbrain.requests, "post") as post:
            with self.assertRaisesRegex(ValueError, "Image data is empty"):
                Vbrain.vision_brain("")
        post.assert_not_called()


class ModelRouterTests(unittest.TestCase):
    def test_routes_short_and_complex_requests(self):
        router = ModelRouter(fast_model="fast-local", reasoning_model="reasoning-local")

        self.assertEqual(router.route("Hi ASTRA").model, "fast-local")
        self.assertEqual(router.route("Analyze this Python stack trace").model, "reasoning-local")
        self.assertEqual(router.route("Anything", explicit_model="manual-local").model, "manual-local")

    def test_uses_installed_alternative_when_preferred_model_is_missing(self):
        router = ModelRouter(fast_model="fast-local", reasoning_model="reasoning-local")
        router.set_available_models(["fast-local"])
        choice = router.route("Analyze this proof")
        self.assertEqual(choice.model, "fast-local")
        self.assertEqual(choice.tier, "fast")


class SettingsTests(unittest.TestCase):
    def test_preferences_persist_between_store_instances(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            SettingsStore(path).update(model="qwen2.5-coder:7b", auto_model=False)
            loaded = SettingsStore(path)

            self.assertEqual(loaded.get("model"), "qwen2.5-coder:7b")
            self.assertFalse(loaded.get("auto_model"))


class FileToolTests(unittest.TestCase):
    def test_file_tools_stay_in_root_and_gate_delete(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "notes.txt"
            target.write_text("ASTRA notes", encoding="utf-8")
            registry = create_default_registry()
            with patch.dict("os.environ", {"ASTRA_FILE_ROOTS": str(root)}):
                self.assertEqual(registry.execute("file_read", {"path": str(target)})["result"], "ASTRA notes")
                blocked = registry.execute("file_read", {"path": str(root.parent / "outside.txt")})
                self.assertFalse(blocked["success"])

                request = registry.execute("file_delete", {"path": str(target)})
                self.assertTrue(request["confirmation_required"])
                self.assertTrue(target.exists())

                deleted = registry.execute(
                    "file_delete", {"path": str(target)}, confirmation_granted=True
                )
                self.assertTrue(deleted["success"])
                self.assertFalse(target.exists())

    def test_destructive_local_action_requires_exact_confirmation(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory, "remove-me.txt")
            target.write_text("keep until confirmed", encoding="utf-8")
            with patch.dict("os.environ", {"ASTRA_FILE_ROOTS": directory}):
                router = LocalToolRouter(create_default_registry())
                request = router.execute(f"delete file {target}")
                self.assertIn("confirm file action", request["content"])
                self.assertTrue(target.exists())
                phrase = router.pending_confirmation["confirmation_phrase"]
                done = router.execute(phrase)

            self.assertIn("Deleted file", done["content"])
            self.assertFalse(target.exists())

    def test_application_launcher_uses_allowlist(self):
        from Automation import open_App as app_module

        fake_process = type("Process", (), {"pid": 42})()
        registry = create_default_registry()
        with patch.object(app_module.shutil, "which", return_value="C:/Windows/notepad.exe"), \
             patch.object(app_module.subprocess, "Popen", return_value=fake_process) as popen:
            result = registry.execute("open_application", {"app": "notepad"})
        self.assertTrue(result["success"])
        self.assertEqual(result["result"]["pid"], 42)
        popen.assert_called_once_with(["C:/Windows/notepad.exe"])

        rejected = registry.execute("open_application", {"app": "powershell -command remove-item"})
        self.assertFalse(rejected["success"])

    def test_desktop_control_click_requires_confirmation_and_exact_phrase(self):
        from Automation import windows_uia

        with patch.object(
            windows_uia, "click_control",
            return_value={"window": "Sales.xlsx - Excel", "control": "Save", "clicked": True},
        ) as click_control:
            registry = create_default_registry()
            router = LocalToolRouter(registry)
            request = router.execute('click control "Save" in window "Sales.xlsx - Excel"')
            self.assertIn("confirm desktop action ui_control_click", request["content"])
            click_control.assert_not_called()
            phrase = router.pending_confirmation["confirmation_phrase"]
            result = router.execute(phrase)
            self.assertEqual(
                router.route('bấm điều khiển "Save" trong cửa sổ "Sales.xlsx - Excel"')[0],
                "ui_control_click",
            )
            text_route = router.route(
                'nhập văn bản vào điều khiển "Search" trong cửa sổ "Browser" thành "ASTRA"'
            )
            self.assertEqual(text_route[0], "ui_control_set_text")
            self.assertEqual(text_route[1]["text"], "ASTRA")

        self.assertIn("Clicked Save", result["content"])
        click_control.assert_called_once_with(
            window_title="Sales.xlsx - Excel", control_name="Save"
        )

    def test_window_inspection_uses_exact_title(self):
        from Automation import windows_uia

        class FakeWindow:
            def __init__(self, title):
                self.title = title

            def window_text(self):
                return self.title

        class FakeDesktop:
            def windows(self):
                return [FakeWindow("Sales.xlsx - Excel"), FakeWindow("Excel Options")]

        with patch.object(windows_uia, "_desktop", return_value=FakeDesktop()):
            self.assertEqual(
                windows_uia._find_window("Excel Options").window_text(),
                "Excel Options",
            )
            with self.assertRaisesRegex(LookupError, "exact title"):
                windows_uia._find_window("Excel")


class OfficeToolTests(unittest.TestCase):
    def test_office_mutations_require_confirmation_before_com_execution(self):
        registry = create_default_registry()
        word = registry.execute(
            "office_word_append", {"path": "report.docx", "content": "Add this paragraph."}
        )
        chart = registry.execute("office_excel_chart", {"path": "sales.xlsx"})

        self.assertTrue(word["confirmation_required"])
        self.assertTrue(chart["confirmation_required"])

    def test_excel_values_neutralize_formula_like_text_and_validate_shape(self):
        from Automation.office_automation import _validated_rows

        rows, row_count, column_count = _validated_rows([
            ["Product", "Comment"],
            ["Notebook", "=HYPERLINK(\"https://example.invalid\")"],
        ])
        self.assertEqual((row_count, column_count), (2, 2))
        self.assertTrue(rows[1][1].startswith("'="))
        with self.assertRaisesRegex(ValueError, "same number of columns"):
            _validated_rows([["A", "B"], ["C"]])

    def test_word_and_excel_commands_route_to_native_office_tools(self):
        router = LocalToolRouter(create_default_registry())
        word = router.route(
            'create word document "report.docx" with title "Quarterly Report" and content "Sales increased."'
        )
        workbook = router.route(
            'create excel workbook "sales.xlsx" data [["Item","Revenue"],["A",20]]'
        )

        self.assertEqual(word[0], "office_word_create")
        self.assertEqual(word[1]["title"], "Quarterly Report")
        self.assertEqual(workbook[0], "office_excel_create")
        self.assertEqual(workbook[1]["rows"][1][1], 20)

    def test_local_router_keeps_requested_source_file_type(self):
        router = LocalToolRouter(create_default_registry())
        self.assertEqual(
            router.route("create python file named notes"),
            ("file_create", {"path": "notes.py"}),
        )

    def test_runtime_uses_scoped_file_search_without_model_call(self):
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, "assignment.txt").write_text("question", encoding="utf-8")
            runtime = AstraRuntime()
            runtime._client_for = lambda _model: (_ for _ in ()).throw(AssertionError("model should not run"))
            with patch.dict("os.environ", {"ASTRA_FILE_ROOTS": directory}):
                result = runtime.ask_full("find files assignment", tools=[])

        self.assertEqual(result["engine"], "astra_local_tools")
        self.assertIn("assignment.txt", result["content"])


if __name__ == "__main__":
    unittest.main()
