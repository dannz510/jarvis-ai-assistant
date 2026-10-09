# ASTRA / OpenJarvis upgrade plan

## Goal

Make the desktop assistant respond reliably, keep normal local requests under a 30-second UI wait, accept offline microphone input, and make its local integrations explicit and safe. The configured target is `qwen2.5-coder:7b` on Ollama. On this Intel CPU-only machine, latency depends on prompt size and model load; the app can enforce a response deadline, but cannot guarantee that every 7B request finishes before it.

## Audit findings

1. **Voice agent startup stopped silently.** `co_brain.py` passed `stop_event` to `listen()`, but the listener did not accept it. The caller swallowed the exception and stopped the voice loop.
2. **Voice commands could be truncated.** Vosk partial hypotheses were written as complete requests while the checker polled the same file every 50 ms.
3. **Repeated commands could be ignored.** The checker retained the previous transcript even after the input file was cleared.
4. **Inference had no wall-clock deadline.** A slow OpenJarvis/Ollama call could leave the chat button waiting indefinitely. The 7B model's measured cold start is a meaningful part of the wait on CPU.
5. **TTS blocked command handling.** `speak()` joined both audio and a character-by-character console animation; a spoken answer could hold up the caller for its full duration.
6. **Setup had an import-time side effect.** Importing `setup.py` recursively ran pip. The voice code also depends on Vosk, which was absent from the requirements list.
7. **Orphan cleanup needs a reference pass.** The tree includes tracked bytecode, generated media, logs, and legacy modules. Some are user data or currently imported; deleting them automatically would risk losing local state.

## Work completed in this pass

- Set the default model to `qwen2.5-coder:7b`; kept `ASTRA_MODEL` as an override.
- Added a 25-second inference deadline, a single-inference guard, short prompts/history, a 72-token output limit, and an Ollama warm-up on startup.
- Fixed listener stop-event handling; submit only completed Vosk utterances; reset consumed-input state so identical commands can be repeated.
- Added protection against the microphone transcribing ASTRA's own queued speech.
- Changed speech output to a serial background queue and removed the artificial typing delay. Pygame now initializes only for optional remote audio.
- Added Vosk to requirements, replaced recursive installation in `setup.py` with packaging metadata, corrected README model/voice instructions, and added `.gitignore`.
- Kept the existing native Qt command center and animated orb. No broad source-file deletion was performed.

## Remaining roadmap

### Phase 1 — Reliable local conversation

- Validate Ollama health and selected model at startup; show actionable model-load, timeout, and offline states in the UI.
- Expose a 1.5B fallback selector and remember the user's selected model. Show a warm-up indicator instead of implying the model is ready before Ollama responds.
- Test representative English and Vietnamese prompts on the actual machine. Tune context/output limits from measured token rates and keep the UI deadline at 25 seconds.
- Ensure tool calls have their own deadline and report partial tool status instead of waiting silently.

### Phase 2 — Voice that works in daily use

- Add microphone selection, input-level meter, push-to-talk, wake-word mode, and a visible transcript preview.
- Bundle or guide installation of a Vietnamese Vosk model; the currently present model is English. Report missing model/PyAudio/device errors in the app, not only the terminal.
- Add voice activity detection and echo handling, then verify repeated turns and stopping/restarting the listener.
- Add voice/rate/volume controls and make the welcome greeting a user-configurable startup option.

### Phase 3 — Interactive command center

- Evolve the current Qt orb with mouse-driven rotation, audio-reactive pulse, distinct listening/thinking/speaking/error states, and reduced-motion/low-power mode.
- Make the dashboard metrics reflect real Ollama, mic, speaker, memory, tool, and system status rather than static sample values.
- Add searchable conversation history, cancellable requests, settings persistence, and visible per-request timing.

### Phase 4 — Local apps, files, and web

- Create a permissioned tool registry for app launch, file/folder search and read/write, browser search, and selected workflows. Show the exact target and ask before destructive or external actions.
- Restrict file tools to user-selected roots, validate paths, and use allowlists for app launch. Keep web search/network use explicit and show source links.
- Add Google integration through OAuth only when configured by the user; do not store passwords or silently automate logged-in browser sessions.
- Add integration-level timeouts, retries where safe, and clear action logs.

### Phase 5 — Repository cleanup and release quality

- Build an import/reference map before removing legacy modules; preserve logs, alarm schedules, memories, and user media.
- Move runtime data to a documented app-data directory, separate it from source, and migrate existing files without deleting originals.
- Pin and document tested dependency versions; replace fragile Windows-only or abandoned packages where practical.
- Run static checks plus a manual acceptance matrix for text chat, tools, voice start/stop, speech output, model timeout, and Windows launch.

## Acceptance targets

- Text chat always exits the waiting state within 25 seconds and explains timeout clearly.
- Warm, short 7B requests meet the 30-second target on this machine; if not, the UI recommends the 1.5B fallback.
- Voice start reports mic/model errors visibly, completed phrases are submitted once, and identical phrases work repeatedly.
- TTS never blocks typing or microphone lifecycle, and ASTRA does not answer its own voice.
- App/file/web actions show what they will touch and respect their configured permission boundary.

## ASTRA master-spec implementation status (2026-10-08)

This section records the current work against the user-provided ASTRA master specification. Its proposed directory tree is illustrative; implementation stays in the repository's existing structure. Assistant identity is ASTRA and owner is Dannz. Treat the earlier roadmap above as historical audit notes where it conflicts with this current status.

### Delivered in the current worktree

- Conversation state/event primitives, bounded recent turns, basic working context, app/file reference resolution, and model routing between local Ollama tiers.
- A configurable local memory store with relevance retrieval, importance/recency ranking, optional embeddings, memory controls, and save/ask/do-not-save policy handling.
- Persistent task records for current app/file, active step, completed steps, observations, errors, and artifacts; sensitive-looking task text is rejected before storage.
- A scoped file agent for common text/document formats, local image analysis, safe ZIP extraction, allowlisted app launch, and explicit confirmation for destructive actions.
- Local Vosk transcript buffering with an incomplete-clause grace period, transcript preview, microphone level, and phrase-triggered TTS cancellation.
- WebRTC VAD using 20 ms frames, a short activity hangover, adaptive RMS fallback, and a visible listening/pause transition in the orb.
- A Windows UIA adapter for visible-window listing, exact-title inspection/focus, and uniquely named controls; click and text actions are confirmation-gated.
- Local Ollama vision support and UI controls for memory, model routing, and runtime state.
- Targeted unit coverage for state, context, model routing, memory, file permissions, speech buffering, and local vision request construction.

### Still required for the requested quality bar

- Semantic end-of-turn detection with genuine streaming partial ASR; WebRTC VAD now classifies speech/pause, while Vosk endpoints and grammar heuristics still make the final turn decision.
- Full-duplex barge-in, reliably interruptible TTS across all providers, and actual TTS audio analysis for the orb.
- Provider adapters beyond Ollama, plus configurable independent speech, vision, reasoning, and embedding providers.
- Complete durable plan/tool/observe/verify/replan loops with live progress, recovery, and user-visible audit history. The current task store records requests/results but does not yet orchestrate long-running multi-step plans.
- Dedicated Word, Excel, PowerPoint, browser, and terminal agents with post-action verification. The initial UIA adapter only handles generic accessible controls and has no app-specific action plans yet.
- Screen element recognition/grounding, safer computer-control permissions, and a user-facing approval workflow.
- A GPU-based procedural Neural Core, audio-reactive output, adaptive quality, and visual-state debugging. Current Qt orb remains a stateful 2D renderer.
- End-to-end acceptance on the actual microphone, TTS device, camera, Ollama server, and desktop applications.

### Current verification

- The targeted suite currently covers the behavior listed above; rerun it after each integration change.
- Hardware-dependent and end-to-end behavior has not been verified. Do not describe unimplemented integrations as working.
