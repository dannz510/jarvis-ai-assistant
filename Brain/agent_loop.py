"""Autonomous ReAct agent loop with durable execution.

Implements the active-agent loop for ASTRA: the LLM reasons (Thought),
picks a tool (Action), observes the real result on the machine
(Observation), and repeats until the goal is complete. Every step is
journaled to SQLite so an interrupted run can resume where it stopped.

Ollama memory optimization (16GB RAM target):
- keep_alive=0 releases the model from RAM immediately after each call
- num_ctx is capped (4096 coder / 2048 vision) to bound KV-cache RAM
- quantized q4_K_M models are expected (see docs/UPGRADE_ROADMAP.md)
"""

import json
import os
import re
import sqlite3
import subprocess
import time
import uuid
from pathlib import Path

import ollama

from Brain.logger import get_logger
from Features import file_agent

logger = get_logger(__name__)

CODER_MODEL = os.environ.get("ASTRA_CODER_MODEL", "qwen2.5-coder:7b")
VISION_MODEL = os.environ.get("ASTRA_VISION_MODEL", "qwen2-vl:2b")
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
CODER_NUM_CTX = int(os.environ.get("ASTRA_CODER_NUM_CTX", "4096"))
VISION_NUM_CTX = int(os.environ.get("ASTRA_VISION_NUM_CTX", "2048"))
MAX_STEPS = int(os.environ.get("ASTRA_AGENT_MAX_STEPS", "10"))
COMMAND_TIMEOUT = int(os.environ.get("ASTRA_COMMAND_TIMEOUT", "30"))
MAX_OUTPUT_CHARS = 4000
MAX_FILE_READ_CHARS = 100000

_BLOCKED_COMMAND_PATTERNS = (
    "format ", "mkfs", "del /f /s", "del /s /q", "rmdir /s /q", "rd /s /q",
    "shutdown", "shutdown.exe", "taskkill /f /im explorer", ":()", "chmod -r 777 /",
    "rm -rf /", "rm -rf /*", "> /dev/sd", "dd if=", "powershell -enc",
    "certutil -decode", "reg delete hklm", "bcdedit", "wmic os delete",
    "remove-item -recurse -force c:\\", "remove-item -recurse -force /",
)

_USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
               "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")


class AgentJournal:
    """Durable execution journal backed by SQLite."""

    def __init__(self, db_path=None):
        path = db_path or os.environ.get(
            "ASTRA_AGENT_DB",
            str(Path.home() / ".astra" / "agent_journal.sqlite3"),
        )
        self.db_path = Path(path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS runs ("
                "run_id TEXT PRIMARY KEY, goal TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'running',"
                " model TEXT, created_at REAL, updated_at REAL, summary TEXT)"
            )
            conn.execute(
                "CREATE TABLE IF NOT EXISTS steps ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT NOT NULL,"
                " step INTEGER NOT NULL, thought TEXT, action TEXT,"
                " action_input TEXT, observation TEXT, status TEXT NOT NULL DEFAULT 'pending',"
                " created_at REAL)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_steps_run ON steps(run_id, step)"
            )

    def create_run(self, goal, model):
        run_id = uuid.uuid4().hex[:12]
        now = time.time()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO runs (run_id, goal, status, model, created_at, updated_at)"
                " VALUES (?, ?, 'running', ?, ?, ?)",
                (run_id, goal, model, now, now),
            )
        return run_id

    def append_step(self, run_id, step, thought, action, action_input, observation, status="completed"):
        now = time.time()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO steps (run_id, step, thought, action, action_input,"
                " observation, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (run_id, step, thought, action, json.dumps(action_input, ensure_ascii=False),
                 observation, status, now),
            )
            conn.execute("UPDATE runs SET updated_at = ? WHERE run_id = ?", (now, run_id))

    def finish_run(self, run_id, status, summary=""):
        now = time.time()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE runs SET status = ?, updated_at = ?, summary = ? WHERE run_id = ?",
                (status, now, summary, run_id),
            )

    def get_run(self, run_id):
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM runs WHERE run_id = ?", (run_id,)).fetchone()
            if row is None:
                return None
            steps = conn.execute(
                "SELECT * FROM steps WHERE run_id = ? ORDER BY step", (run_id,)
            ).fetchall()
        return {
            "run_id": row["run_id"],
            "goal": row["goal"],
            "status": row["status"],
            "model": row["model"],
            "summary": row["summary"],
            "steps": [dict(step) for step in steps],
        }

    def list_runs(self, limit=20):
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT run_id, goal, status, model, updated_at FROM runs"
                " ORDER BY updated_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(row) for row in rows]


def _truncate(text, limit=MAX_OUTPUT_CHARS):
    text = str(text)
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n... [truncated {len(text) - limit} chars]"


def _check_command_safety(cmd):
    lowered = str(cmd).casefold()
    for pattern in _BLOCKED_COMMAND_PATTERNS:
        if pattern in lowered:
            raise PermissionError(f"Command blocked by ASTRA safety policy: {pattern}")


def execute_command(cmd):
    """Run a shell command (PowerShell/CMD) and return stdout/stderr."""
    _check_command_safety(cmd)
    try:
        result = subprocess.run(
            str(cmd), shell=True, capture_output=True, text=True,
            timeout=COMMAND_TIMEOUT, encoding="utf-8", errors="replace",
        )
        output = f"EXIT CODE: {result.returncode}\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        if result.returncode != 0:
            output += (
                "\nThe command failed. If the error is unclear, call google_search_fix "
                "with the STDERR text to find a solution before retrying."
            )
        return _truncate(output)
    except subprocess.TimeoutExpired:
        return f"Command timed out after {COMMAND_TIMEOUT}s."
    except Exception as exc:
        return f"Execution error: {exc}"


def write_file(path, content):
    """Create or overwrite a UTF-8 file. Use RELATIVE paths only (e.g. "notes.txt" or "subdir/notes.txt"). Absolute paths are rejected."""
    resolved = file_agent.resolve_allowed_path(path)
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text(str(content), encoding="utf-8")
    return f"File written successfully: {resolved} ({len(str(content))} chars)"


def read_file(path):
    """Read a text file. Use RELATIVE paths only (e.g. "notes.txt"). Absolute paths are rejected."""
    resolved = file_agent.resolve_allowed_path(path, must_exist=True)
    text = resolved.read_text(encoding="utf-8", errors="replace")
    return _truncate(text, MAX_FILE_READ_CHARS)


def list_directory(path="."):
    """List files and folders with sizes inside the configured ASTRA roots."""
    resolved = file_agent.resolve_allowed_path(path, must_exist=True)
    if not resolved.is_dir():
        raise NotADirectoryError(f"Not a directory: {resolved}")
    entries = []
    for child in sorted(resolved.iterdir()):
        try:
            if child.is_dir():
                entries.append(f"[DIR]  {child.name}/")
            else:
                size = child.stat().st_size
                entries.append(f"[FILE] {child.name} ({size} bytes)")
        except OSError:
            entries.append(f"[?]    {child.name}")
    header = f"Contents of {resolved} ({len(entries)} entries):"
    return _truncate("\n".join([header] + entries), MAX_OUTPUT_CHARS)


def edit_file_patch(path, find, replace):
    """Replace occurrences of `find` with `replace` in a file. Use RELATIVE paths only. Absolute paths are rejected."""
    resolved = file_agent.resolve_allowed_path(path, must_exist=True)
    text = resolved.read_text(encoding="utf-8", errors="replace")
    if str(find) not in text:
        return f"Pattern not found in {resolved}. No changes made."
    count = text.count(str(find))
    updated = text.replace(str(find), str(replace))
    resolved.write_text(updated, encoding="utf-8")
    return f"Replaced {count} occurrence(s) in {resolved}"


def _ddg_search(query, limit=5):
    import requests
    from bs4 import BeautifulSoup

    try:
        response = requests.post(
            "https://html.duckduckgo.com/html/",
            data={"q": query},
            headers={"User-Agent": _USER_AGENT},
            timeout=12,
        )
        response.raise_for_status()
    except Exception as exc:
        return f"Search service unavailable: {exc}"
    soup = BeautifulSoup(response.text, "html.parser")
    results = []
    for item in soup.select(".result")[:limit]:
        link = item.select_one(".result__a")
        snippet = item.select_one(".result__snippet")
        if link is None:
            continue
        title = link.get_text(strip=True)
        href = link.get("href", "")
        match = re.search(r"uddg=([^&]+)", href)
        if match:
            from urllib.parse import unquote
            href = unquote(match.group(1))
        body = snippet.get_text(strip=True) if snippet else ""
        results.append(f"- {title}\n  {href}\n  {body}")
    if not results:
        return "No results found for this query."
    return "\n\n".join(results)


def web_search(query):
    """Search the web (DuckDuckGo, no API key required) and return snippets."""
    return _truncate(_ddg_search(query), MAX_OUTPUT_CHARS)


def google_search_fix(error_message):
    """Search the web for a solution to a system error or traceback."""
    query = f"{str(error_message)[:200]} solution fix"
    return _truncate(_ddg_search(query), MAX_OUTPUT_CHARS)


def fetch_url(url):
    """Download a web page and return its readable text content."""
    import requests
    from bs4 import BeautifulSoup

    parsed = url.split("://", 1)
    if len(parsed) != 2 or parsed[0] not in ("http", "https") or not parsed[1]:
        raise ValueError("Only http/https URLs are allowed.")
    try:
        response = requests.get(url, headers={"User-Agent": _USER_AGENT}, timeout=15)
        response.raise_for_status()
    except Exception as exc:
        return f"Could not fetch URL: {exc}"
    soup = BeautifulSoup(response.text, "html.parser")
    for tag in soup(["script", "style", "noscript", "nav", "footer", "header"]):
        tag.decompose()
    text = soup.get_text(separator="\n", strip=True)
    return _truncate(text, MAX_OUTPUT_CHARS)


def take_screenshot():
    """Capture the screen and save a PNG for visual analysis."""
    import pyautogui

    pyautogui.FAILSAFE = True
    directory = Path.home() / ".astra" / "screenshots"
    directory.mkdir(parents=True, exist_ok=True)
    filename = directory / f"screen_{time.strftime('%Y%m%d_%H%M%S')}.png"
    image = pyautogui.screenshot()
    image.save(filename)
    width, height = image.size
    return (
        f"Screenshot saved to {filename} ({width}x{height}). "
        "Use click_coordinate(x, y) to click a point on this screen."
    )


def click_coordinate(x, y):
    """Move the mouse to (x, y) and click."""
    import pyautogui

    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0.2
    width, height = pyautogui.size()
    x, y = int(x), int(y)
    if not (0 <= x < width and 0 <= y < height):
        raise ValueError(f"Coordinate ({x}, {y}) outside screen {width}x{height}.")
    pyautogui.moveTo(x, y, duration=0.3)
    pyautogui.click()
    return f"Clicked at ({x}, {y})"


def type_text(text):
    """Type text at the current cursor position (unicode-safe via clipboard)."""
    import pyautogui

    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0.2
    text = str(text)
    if text.isascii():
        pyautogui.typewrite(text, interval=0.01)
        return f"Typed {len(text)} characters."
    try:
        subprocess.run(["clip"], input=text, text=True, check=True, timeout=10)
        pyautogui.hotkey("ctrl", "v")
        return f"Pasted {len(text)} characters via clipboard."
    except Exception:
        pyautogui.typewrite(text.encode("ascii", "ignore").decode(), interval=0.01)
        return "Typed ASCII-safe subset of the text (non-ASCII dropped)."


def press_key(key):
    """Press a single key or named combination (e.g. 'enter', 'ctrl+c')."""
    import pyautogui

    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0.2
    key = str(key).lower()
    if "+" in key:
        parts = [part.strip() for part in key.split("+")]
        pyautogui.hotkey(*parts)
    else:
        pyautogui.press(key)
    return f"Pressed key: {key}"


def open_application(app_name):
    """Launch an allowlisted desktop application."""
    from Automation.open_App import open_App

    process = open_App(str(app_name))
    return f"Launched {app_name} (pid {getattr(process, 'pid', 'n/a')})"


TOOLS = {
    "execute_command": {
        "func": execute_command,
        "description": "Run a shell command (PowerShell/CMD). Returns exit code, stdout, stderr.",
        "params": {"cmd": "string"},
    },
    "write_file": {
        "func": write_file,
        "description": "Create or overwrite a UTF-8 file. Use RELATIVE paths only "
                       "(e.g. 'notes.txt' or 'subdir/notes.txt'). Absolute paths and paths "
                       "outside the project root are rejected.",
        "params": {"path": "string", "content": "string"},
    },
    "read_file": {
        "func": read_file,
        "description": "Read a text file. Use RELATIVE paths only (e.g. 'notes.txt').",
        "params": {"path": "string"},
    },
    "list_directory": {
        "func": list_directory,
        "description": "List files and folders with sizes. Use RELATIVE paths only. "
                       "Default '.' lists the current project root.",
        "params": {"path": "string"},
    },
    "edit_file_patch": {
        "func": edit_file_patch,
        "description": "Find and replace text inside a file. Use RELATIVE paths only.",
        "params": {"path": "string", "find": "string", "replace": "string"},
    },
    "web_search": {
        "func": web_search,
        "description": "Search the web and return top result snippets (no API key needed).",
        "params": {"query": "string"},
    },
    "google_search_fix": {
        "func": google_search_fix,
        "description": "Search the web for a fix to a system error or traceback.",
        "params": {"error_message": "string"},
    },
    "fetch_url": {
        "func": fetch_url,
        "description": "Download a web page and return its readable text.",
        "params": {"url": "string"},
    },
    "take_screenshot": {
        "func": take_screenshot,
        "description": "Capture the screen to a PNG file and report its path and size.",
        "params": {},
    },
    "click_coordinate": {
        "func": click_coordinate,
        "description": "Move the mouse to (x, y) and click.",
        "params": {"x": "integer", "y": "integer"},
    },
    "type_text": {
        "func": type_text,
        "description": "Type text at the current cursor position.",
        "params": {"text": "string"},
    },
    "press_key": {
        "func": press_key,
        "description": "Press a key like 'enter' or a combination like 'ctrl+c'.",
        "params": {"key": "string"},
    },
    "open_application": {
        "func": open_application,
        "description": "Launch an allowlisted desktop application by name.",
        "params": {"app_name": "string"},
    },
}

SYSTEM_PROMPT = (
    "You are ASTRA, an autonomous agent operating Dannz's Windows computer. "
    "You complete the user's goal by calling tools in a loop. "
    "Respond with ONLY a JSON object, no markdown fences, no explanation:\n"
    '{"thought": "your reasoning about the next step", '
    '"action": "tool_name", "action_input": {"param": "value"}}\n\n'
    'When the goal is fully complete, respond with: '
    '{"thought": "goal complete", "action": "finish", '
    '"action_input": {"summary": "final report to the user"}}\n\n'
    "Available tools:\n"
    + "\n".join(
        f"- {name}({', '.join(spec['params'])}): {spec['description']}"
        for name, spec in TOOLS.items()
    )
    + "\n\nIMPORTANT: All file paths must be RELATIVE to the project root (e.g. \'file.txt\', \'subdir/file.txt\'). NEVER use absolute paths like C:\\\\ or D:\\\\ -- they will be rejected.\n"
    + "Rules: verify file writes by reading the file back; if a command fails, "
    + "read the error, use google_search_fix if needed, then retry with a corrected command; "
    + "never claim success without an Observation proving it."
)


def _extract_json(text):
    """Parse the model's JSON action, tolerating fences and stray prose."""
    text = str(text).strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end > start:
        try:
            return json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            pass
    return None


class ReActAgent:
    """Thought -> Action -> Observation loop with durable journaling."""

    def __init__(self, model=None, journal=None, on_step=None, max_steps=None):
        self.model = model or CODER_MODEL
        self.journal = journal or AgentJournal()
        self.on_step = on_step
        self.max_steps = max_steps or MAX_STEPS

    def _emit(self, event):
        if self.on_step:
            try:
                self.on_step(event)
            except Exception:
                logger.debug("Agent step callback failed", exc_info=True)

    def _call_model(self, messages):
        return ollama.chat(
            model=self.model,
            messages=messages,
            keep_alive=0,
            options={
                "num_ctx": CODER_NUM_CTX,
                "temperature": 0.1,
                "num_predict": 1024,
            },
        )["message"]["content"]

    def run(self, goal, resume_run_id=None):
        """Execute a goal. Returns the final summary string."""
        run_id = resume_run_id or self.journal.create_run(goal, self.model)
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Goal: {goal}"},
        ]
        start_step = 0
        if resume_run_id:
            recorded = self.journal.get_run(run_id)
            if recorded is None:
                raise ValueError(f"Unknown run_id: {run_id}")
            if recorded["status"] != "running":
                return f"Run {run_id} already finished: {recorded['summary']}"
            for step in recorded["steps"]:
                messages.append({
                    "role": "assistant",
                    "content": json.dumps({
                        "thought": step["thought"], "action": step["action"],
                        "action_input": json.loads(step["action_input"] or "{}"),
                    }, ensure_ascii=False),
                })
                messages.append({
                    "role": "user",
                    "content": f"Observation: {step['observation']}",
                })
            start_step = len(recorded["steps"])
            logger.info(f"Resuming agent run {run_id} at step {start_step}")

        for step_number in range(start_step, self.max_steps):
            self._emit({"type": "thinking", "run_id": run_id, "step": step_number})
            try:
                raw_output = self._call_model(messages)
            except Exception as exc:
                self.journal.finish_run(run_id, "failed", f"Model error: {exc}")
                self._emit({"type": "error", "run_id": run_id, "error": str(exc)})
                return f"Agent model error: {exc}"

            action_data = _extract_json(raw_output)
            if action_data is None:
                messages.append({"role": "assistant", "content": raw_output})
                messages.append({
                    "role": "user",
                    "content": "Invalid response: reply with ONLY the JSON object.",
                })
                self.journal.append_step(
                    run_id, step_number, "parse failure", "invalid", {},
                    "Model did not return valid JSON", status="failed",
                )
                continue

            thought = str(action_data.get("thought", ""))
            action = str(action_data.get("action", ""))
            action_input = action_data.get("action_input", {})
            if not isinstance(action_input, dict):
                action_input = {"value": action_input}

            self._emit({
                "type": "step", "run_id": run_id, "step": step_number,
                "thought": thought, "action": action, "action_input": action_input,
            })
            logger.info(f"Agent step {step_number}: {action} {action_input}")

            if action == "finish":
                summary = action_input.get("summary", action_input.get("value", ""))
                self.journal.finish_run(run_id, "completed", str(summary))
                self._emit({"type": "finish", "run_id": run_id, "summary": str(summary)})
                return str(summary)

            tool = TOOLS.get(action)
            if tool is None:
                observation = (
                    f"Unknown tool '{action}'. Available tools: "
                    f"{', '.join(TOOLS)}. Choose a different tool or call finish."
                )
                status = "failed"
            else:
                try:
                    observation = tool["func"](**action_input)
                    status = "completed"
                except TypeError as exc:
                    observation = (
                        f"Wrong arguments for {action}: {exc}. "
                        f"Expected parameters: {tool['params']}."
                    )
                    status = "failed"
                except Exception as exc:
                    observation = f"Tool error: {exc}"
                    status = "failed"

            # Loop detector: repeated identical (action, input) pairs stall the agent.
            action_key = (action, json.dumps(action_input, sort_keys=True, default=str))
            if not hasattr(self, "_recent_actions"):
                self._recent_actions = []
            self._recent_actions.append(action_key)
            if self._recent_actions.count(action_key) >= 2:
                observation = (
                    "LOOP DETECTED: you repeated the same action 2 times with the same "
                    "input and it keeps failing. DO NOT retry it. Either change the "
                    "parameters (e.g. use a relative path instead of an absolute one, "
                    "or pick a different tool) or call finish and report what you could "
                    "not do. Reply with ONLY the JSON object."
                )
                status = "failed"
            if status == "completed":
                self._recent_actions = []
            if len(self._recent_actions) > 12:
                self._recent_actions = self._recent_actions[-12:]

            self.journal.append_step(
                run_id, step_number, thought, action, action_input,
                str(observation), status=status,
            )
            self._emit({
                "type": "observation", "run_id": run_id, "step": step_number,
                "observation": str(observation), "status": status,
            })
            messages.append({
                "role": "assistant",
                "content": json.dumps(action_data, ensure_ascii=False),
            })
            messages.append({"role": "user", "content": f"Observation: {observation}"})

        self.journal.finish_run(run_id, "max_steps_reached", "Reached the step limit.")
        self._emit({"type": "finish", "run_id": run_id, "summary": "Reached the step limit."})
        return "Reached the maximum number of agent steps without completing the goal."

    def resume(self, run_id):
        """Resume an interrupted run from its durable journal."""
        return self.run("", resume_run_id=run_id)

    def list_runs(self, limit=20):
        return self.journal.list_runs(limit)

    def get_run(self, run_id):
        return self.journal.get_run(run_id)


_agent = None


def get_agent(model=None, on_step=None):
    """Return a shared ReActAgent instance."""
    global _agent
    if _agent is None:
        _agent = ReActAgent(model=model, on_step=on_step)
    elif on_step is not None:
        _agent.on_step = on_step
    return _agent
