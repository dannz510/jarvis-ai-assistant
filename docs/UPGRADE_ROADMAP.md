# ASTRA Upgrade Roadmap

Status: **CORE COMPLETE** (session 2026-10-09)
Owner: Dannz
Language: English

This document records the architectural upgrade plan for ASTRA (OpenJarvis fork).
It converts the assistant from a passive chatbot (Request-Response) into an
autonomous Agent (ReAct loop) that can read/write files, search the web, drive the
mouse/keyboard, and self-heal when a command fails.

## 1. System / File tools ✅ COMPLETE

The LLM cannot touch the disk directly. It gets "arms" as Python functions that
execute through the shell.

- list_directory(path): list files/folders (os.listdir / Get-ChildItem)
- read_file(path): read text files
- write_file(path, content): create or overwrite UTF-8 files
- edit_file_patch(path, find, replace): find-and-replace inside a file
- execute_command(cmd): run shell scripts (PowerShell/CMD)

All file ops are confined to ASTRA_FILE_ROOTS (default: project root) via
Features/file_agent.resolve_allowed_path(). This rejects absolute paths outside
the roots, symlink escapes, and writes outside the boundary.

Implemented in: Brain/agent_loop.py, Features/file_agent.py

## 2. Web search ✅ COMPLETE

- web_search(query): DuckDuckGo HTML scraping (no API key). Returns top snippets.
- google_search_fix(error_message): search for a solution to a system error.
- fetch_url(url): download a page and return readable text (BeautifulSoup).

Trigger: when the agent needs real-time data or a technology it does not know, the
Thought step calls web_search. After a URL is found, fetch_url scrapes the page.

Future: SearXNG self-hosted locally for privacy; Serper / Google Custom Search API.

## 3. Multistep Planner & Durable Execution ✅ COMPLETE

- ReAct loop: Thought -> Action -> Observation, repeat until the goal is done.
- Durable execution: every step is journaled to SQLite
  (~/.astra/agent_journal.sqlite3). If the process crashes or the model times out,
  the run can resume from the last completed step instead of restarting.

Tables: runs (run_id, goal, status, model, created_at, updated_at, summary),
steps (id, run_id, step, thought, action, action_input, observation, status).

Implemented in: Brain/agent_loop.py (AgentJournal, ReActAgent.run/resume)
Also: Brain/multistep_planner.py (rule-based planner, JSON journal files)

## 4. Fast response / high performance (16GB RAM target) ✅ COMPLETE

- Context caching: num_ctx capped per model (4096 coder / 2048 vision).
- keep_alive=0: Ollama releases the model from RAM immediately after each call.
- Quantization: use q4_K_M variants (qwen2.5-coder:7b-instruct-q4_K_M,
  qwen2-vl:2b-instruct-q4_K_M). Never use FP16 originals.
- OLLAMA_MAX_LOADED_MODELS=1 and OLLAMA_NUM_PARALLEL=1 to hold only one model at a
  time and swap them sequentially.
- Streaming output: future work (tune the UI to stream tokens as they arrive).

## 5. OS / GUI agent (Pilot) ✅ COMPLETE

- take_screenshot(): capture the screen to ~/.astra/screenshots/.
- click_coordinate(x, y): move the mouse and click (bounds-checked).
- type_text(text): type at the cursor (unicode-safe via clipboard paste).
- press_key(key): press a key or combo like ctrl+c.
- open_application(app_name): launch an allowlisted app via Automation.open_App.

Safety: pyautogui.FAILSAFE = True (mouse to corner aborts), PAUSE between actions,
coordinate bounds check, command blocklist in execute_command.

## 6. Ollama memory optimization ✅ COMPLETE

- keep_alive=0 in every chat() call.
- num_ctx: 4096 (coder), 2048 (vision).
- Env vars: OLLAMA_MAX_LOADED_MODELS=1, OLLAMA_NUM_PARALLEL=1.
- Modelfile RAM limits: future work.

## 7. UI renovation ✅ COMPLETE (2026-10-09)

The Qt UI (ui.py) is upgraded:
- New "Agent Loop" page showing the live Thought / Action / Observation stream.
- Agent selector gains an "agentic" mode that routes through Brain/agent_loop.py.
- Orb Bridge (Brain/orb_bridge.py) forwards state to the Three.js visualizer
  (public/index.html, public/orb.js, public/audio.js).
- Live step feed emitted via on_step callback.
- **Web Bridge Server** (web_bridge.py) — aiohttp + WebSocket serving `public/` assets and bridging `orb_bridge` events to browser in real-time.
- **Upgraded PyQt OrbVisualizer** (astra_ui/widgets/orb.py) — 13 state profiles, FFT visualizer, 3D node field, particle field, mic-reactive ripples, parallax tilt, progress ring, tool activity text.
- **Modular astra_ui/** package — core/theme, widgets/orb, widgets/panels, widgets/animations, widgets/welcome, widgets/icons, assets.
- **Security/Login UI** (Security/login_ui.py) — Holographic login with starfield, glass container, PIN pad, biometric overlays.

## 8. Security & Auth Layer ✅ COMPLETE (NEW)

- **auth_manager.py** — Central auth orchestration (PIN, password, face, fingerprint, Windows Hello, liveness)
- **pin_auth.py** — PIN hashing/verification (PBKDF2)
- **secure_storage.py** — Encrypted profile storage (Fernet)
- **face_recognition.py** — Face enrollment/verification (OpenCV LBPH)
- **fingerprint.py** — Fingerprint via Windows Biometric Framework
- **liveness.py** — Anti-spoofing texture analysis
- **winbio_wrapper.py** — Windows Hello integration
- **login_ui.py** — Holographic login UI (starfield, glass, PIN pad, biometric overlays)

## 9. Voice Pipeline — IN PROGRESS

- **STT**: NetHyTechSTT/listen.py — Vosk offline (EN + VN models present) ✅
- **TTS**: TextToSpeech/Fast_DF_TTS.py — Windows SAPI + pyttsx3 fallback ✅
- **VAD**: Brain/voice_activity.py — WebRTC VAD + adaptive RMS fallback ✅
- **Speech Turn**: Brain/speech_turn.py — Partial transcript + end-of-turn heuristics ✅
- **Barge-In**: Brain/barge_in.py — Acoustic full-duplex interruption detection (experimental) ⏳

## 10. Vision & Web — IN PROGRESS

- **Vision**: Vision/Vbrain.py — Camera capture + Ollama vision ✅
- **Google Workspace**: Brain/google_workspace.py — Gmail/Calendar/Drive/Docs/Sheets/Slides/Tasks via OAuth ⏳ (requires credentials)
- **Web Search**: Real_Time/ — DuckDuckGo live search ✅
- **Text-to-Image**: TextToImage/gen_image.py ✅

## 11. Remaining Work (Post-Audit 2026-10-09)

| Priority | Task | Status |
|----------|------|--------|
| HIGH | Auto-start `web_bridge.py` with UI; integrate Three.js orb via QWebEngineView | ⏳ |
| HIGH | Wire ReActAgent as default orchestrator for `agentic` mode | ⏳ |
| HIGH | Configure Google OAuth credentials; test Workspace clients | ⏳ |
| MEDIUM | Calibrate acoustic barge-in detector with live microphone | ⏳ |
| MEDIUM | Test full English/Vietnamese voice pipeline with Ollama running | ⏳ |
| MEDIUM | Add WebSocket authentication if exposing beyond localhost | ⏳ |
| MEDIUM | Move runtime data to documented app-data directory | ⏳ |
| LOW | Add RAG local vector DB (ChromaDB/FAISS) for long tasks | ⏳ |
| LOW | Face/Fingerprint/Hello hardware testing | ⏳ |
| LOW | Expanded APP_ALLOWLIST in Automation/open_App.py | ⏳ |
| LOW | Premium UI rebuild (full dark glassmorphism theme) | ⏳ |

## 12. Verification Checklist (2026-10-09 Audit)

- [x] Compile audit: 0/137 Python files failed
- [x] Integration tests: 14/14 passed
- [x] Import graph: Clean one-way deps (no cycles)
- [x] Voice pipeline: STT + TTS + Runtime ask all import/code-path OK
- [x] Agentic agent: ReActAgent instantiation, AgentJournal CRUD all OK
- [x] Dependencies: All required packages installed
- [x] Vosk models: Both EN + VN models present and loadable
- [x] All critical bugs fixed (13 issues)
- [x] All missing stub modules created (5 modules)

---

*Last updated: 2026-10-09*  
*Architect: Kilo (automated comprehensive audit)*  
*Status: 🟢 Core systems operational — ready for live voice testing*