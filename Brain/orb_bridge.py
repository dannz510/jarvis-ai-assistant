"""Bridge between the ASTRA Python core and the Three.js/WebGL Orb visualizer.

The visualizer runs in a separate HTML/JS layer (see public/index.html).
This module exposes a Python API so the agent can update state, audio levels,
and trigger events without touching the browser directly.
"""

import json
import os
import threading
import time
from pathlib import Path
from typing import Callable, Optional

from Brain.logger import get_logger

logger = get_logger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
VISUALIZER_DIR = PROJECT_ROOT / "public"
INDEX_HTML = VISUALIZER_DIR / "index.html"

# Valid visualizer states mapped to agent states.
STATE_MAP = {
    "idle": "idle",
    "listening": "listening",
    "user_paused": "listening",
    "processing": "thinking",
    "thinking": "thinking",
    "tool_selection": "executing",
    "executing": "executing",
    "observing": "executing",
    "responding": "speaking",
    "speaking": "speaking",
    "success": "success",
    "error": "error",
    "interrupted": "interrupted",
    "waiting_for_clarification": "waiting_for_clarification",
    "booting": "booting",
}


class OrbBridge:
    """Thin wrapper that forwards ASTRA events to the WebGL orb."""

    def __init__(self, html_path: Optional[str] = None):
        self.html_path = str(html_path or INDEX_HTML)
        self._state = "idle"
        self._audio_level = 0.0
        self._frequency_bands = {"low": 0.0, "mid": 0.0, "high": 0.0}
        self._progress: Optional[float] = None
        self._tool_activity = ""
        self._subscribers: list[Callable[[dict], None]] = []
        self._lock = threading.RLock()
        self._last_event_at = 0.0

    @property
    def html_url(self) -> str:
        return f"file://{self.html_path}"

    def subscribe(self, callback: Callable[[dict], None]) -> None:
        with self._lock:
            self._subscribers.append(callback)

    def unsubscribe(self, callback: Callable[[dict], None]) -> None:
        with self._lock:
            if callback in self._subscribers:
                self._subscribers.remove(callback)

    def _publish(self, event: dict) -> None:
        with self._lock:
            subscribers = tuple(self._subscribers)
        for callback in subscribers:
            try:
                callback(event)
            except Exception as exc:
                logger.warning("Orb subscriber raised: %s", exc)

    def set_state(self, state: str) -> None:
        normalized = STATE_MAP.get(str(state).casefold(), "idle")
        with self._lock:
            if normalized == self._state:
                return
            self._state = normalized
        self._publish({
            "type": "state",
            "state": normalized,
            "timestamp": time.time(),
        })
        logger.debug("Orb state -> %s", normalized)

    def set_audio_level(self, value: float) -> None:
        clamped = max(0.0, min(1.0, float(value)))
        with self._lock:
            self._audio_level = clamped
        self._publish({
            "type": "audio",
            "level": clamped,
            "bands": dict(self._frequency_bands),
        })

    def set_frequency_bands(self, low: float = 0.0, mid: float = 0.0, high: float = 0.0) -> None:
        with self._lock:
            self._frequency_bands = {
                "low": max(0.0, min(1.0, float(low))),
                "mid": max(0.0, min(1.0, float(mid))),
                "high": max(0.0, min(1.0, float(high))),
            }
            self._audio_level = max(self._frequency_bands.values())
        self._publish({
            "type": "audio",
            "level": self._audio_level,
            "bands": dict(self._frequency_bands),
        })

    def set_progress(self, value: Optional[float]) -> None:
        with self._lock:
            self._progress = None if value is None else max(0.0, min(1.0, float(value)))
        self._publish({"type": "progress", "value": self._progress})

    def set_tool_activity(self, tool_name: str) -> None:
        with self._lock:
            self._tool_activity = str(tool_name or "")
            self._state = "executing"
        self._publish({
            "type": "tool",
            "tool": self._tool_activity,
            "state": self._state,
        })

    def trigger_pulse(self) -> None:
        self._publish({"type": "pulse", "timestamp": time.time()})

    def trigger_success(self) -> None:
        self.set_state("success")
        self.trigger_pulse()

    def trigger_error(self) -> None:
        self.set_state("error")
        self.trigger_pulse()

    def interrupt(self) -> None:
        self.set_state("interrupted")
        self._publish({"type": "interrupt", "timestamp": time.time()})

    def reset(self) -> None:
        with self._lock:
            self._state = "idle"
            self._audio_level = 0.0
            self._progress = None
            self._tool_activity = ""
        self._publish({"type": "reset", "state": "idle"})

    def status(self) -> dict:
        with self._lock:
            return {
                "state": self._state,
                "audio_level": self._audio_level,
                "frequency_bands": dict(self._frequency_bands),
                "progress": self._progress,
                "tool_activity": self._tool_activity,
                "html_url": self.html_url,
            }


_orb_bridge: Optional[OrbBridge] = None


def get_orb_bridge() -> OrbBridge:
    """Return the process-wide OrbBridge singleton."""
    global _orb_bridge
    if _orb_bridge is None:
        _orb_bridge = OrbBridge()
    return _orb_bridge