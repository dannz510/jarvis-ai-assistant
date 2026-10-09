# ASTRA Changelog

## 2026-10-09 — Comprehensive Audit & Bug Fixes (Dannz)

### Fixed (Critical)
- **jarvis_runtime.py**: `task_store`/`task_id` used before definition in `agentic` branch (UnboundLocalError)
- **jarvis_runtime.py**: Early return from `_resolve_memory_confirmation` without setting `completed` event (thread deadlock)
- **co_brain.py**: `random.choice()` at module import crashes if dialog lists empty (ImportError)
- **astra_ui/widgets/orb.py**: List modification during iteration in `_tick()` (RuntimeError)
- **Security/auth_manager.py**: `base64` used without import; plaintext password stored (NameError + Security)
- **Brain/agent_loop.py**: Unterminated string literal (quote mismatch, em dash, backslash escaping) (SyntaxError)
- **Brain/agent_loop.py**: Missing `+` prefix on string concatenation lines (SyntaxError)
- **Automation/Youtube_play_back.py**: Module deleted but still imported in `Automation_Brain.py` (ModuleNotFoundError)
- **ui.py**: `load_assets(QApplication.instance())` called before QApplication created
- **ui.py**: Agent validation excluded `"agentic"` from allowed set
- **ui.py**: `_poll_log` re-processes entire log on truncation causing duplicate transcripts
- **ui.py**: Duplicate import blocks for `astra_ui` components
- **fix_newlines.py**, **test_pyaudio.py**: UTF-8 BOM / UTF-16LE encoding issues

### Added
- **Features/mike_health.py** — Microphone presence/level check via WMI
- **Features/speaker_health.py** — Speaker/playback device check via WMI
- **Features/br_persentage.py** — Brightness percentage query (WMI + ddcutil fallback)
- **Features/set_br.py** — Set brightness (WMI for laptop, ddcutil for external)
- **Features/check_running_app.py** — Top CPU/memory processes via psutil
- **web_bridge.py** — aiohttp + WebSocket server serving `public/` + bridging `orb_bridge` events to browser

### Changed
- **ui.py**: Renamed `ui/` package to `astra_ui/` to avoid name shadowing with `ui.py` entry point
- **ui.py**: Consolidated duplicate import blocks
- **ui.py**: Added `"agentic"` to allowed agent set
- **jarvis_runtime.py**: Moved `task_store = self._task_store()` before agentic branch
- **jarvis_runtime.py**: Create `completed` event before `_resolve_memory_confirmation` check
- **co_brain.py**: Deferred `random.choice()` to runtime via `_init_random_dialogs()`
- **astra_ui/widgets/orb.py**: Replaced list iteration with list comprehension for `_ripples`
- **Security/auth_manager.py**: Added `import base64` at module level; store password hash not plaintext
- **Brain/agent_loop.py**: Fixed quote mismatch, em dash, backslash escaping in SYSTEM_PROMPT
- **Brain/agent_loop.py**: Added missing `+` prefixes on Rules continuation lines

### Removed
- All temporary fix scripts (`fix_*.py`, `fixit*.py`, `test_fast.py`, etc.)
- Broken files in `scripts/` directory

### Verification
- **Compile audit**: 0/137 Python files failed
- **Integration tests**: 14/14 passed (Runtime, Settings, Memory, Tasks, Local Tools, Agent State, Orb Bridge, Auth, Features, UI, Web Bridge, Automation, Co-brain, Agentic)
- **Import graph**: Clean one-way deps (no cycles)
- **Voice pipeline**: STT (Vosk) + TTS (SAPI) + Runtime ask all import/code-path OK
- **Agentic agent**: ReActAgent instantiation, AgentJournal CRUD all OK
- **Dependencies**: All required packages installed (vosk, opencv, scikit-learn, aiohttp, etc.)
- **Vosk models**: Both `vosk-model-small-en-us-0.15` and `vosk-model-small-vn-0.4` present and loadable

## 2026-10-08 — Agentic upgrade (Dannz)

### Added
- Brain/agent_loop.py — ReAct agent loop (Thought -> Action -> Observation)
  with durable SQLite journaling and Ollama memory optimization.
  Tools: execute_command, write_file, read_file, list_directory,
  edit_file_patch, web_search, google_search_fix, fetch_url,
  take_screenshot, click_coordinate, type_text, press_key, open_application.
- docs/UPGRADE_ROADMAP.md — full architecture upgrade plan.

### Changed
- jarvis_runtime.py — added "agentic" agent mode routed through ReActAgent.
- ui.py — Agent Loop page, live step feed, agentic agent selector.

### Security
- execute_command blocklist (format, rm -rf, shutdown, encoded PowerShell, etc.).
- File tools confined to ASTRA_FILE_ROOTS via resolve_allowed_path.
- pyautogui FAILSAFE enabled; click coordinates bounds-checked.

### Verified
- python -m unittest -v test_agent_context — 33/33 pass.