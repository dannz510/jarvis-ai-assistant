"""Persistent user preferences stored outside the source tree."""

import json
import os
from pathlib import Path
import threading


DEFAULT_SETTINGS = {
    "auto_model": True,
    "model": "",
    "agent": "simple",
    "enabled_tools": ["calculator", "web_search", "think"],
    "memory_enabled": True,
    "memory_policy": "explicit",
    "reduced_motion": False,
}


def default_settings_path():
    app_data = os.environ.get("APPDATA") or os.environ.get("LOCALAPPDATA")
    root = Path(app_data) if app_data else Path.home() / "AppData" / "Roaming"
    return root / "ASTRA" / "settings.json"


class SettingsStore:
    def __init__(self, path=None):
        self.path = Path(path) if path else default_settings_path()
        self._lock = threading.RLock()
        self._values = dict(DEFAULT_SETTINGS)
        self.load()

    def load(self):
        with self._lock:
            try:
                loaded = json.loads(self.path.read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    self._values.update(loaded)
            except (OSError, UnicodeError, json.JSONDecodeError):
                pass
            enabled_tools = self._values.get("enabled_tools", DEFAULT_SETTINGS["enabled_tools"])
            if not isinstance(enabled_tools, list):
                enabled_tools = DEFAULT_SETTINGS["enabled_tools"]
            self._values["enabled_tools"] = list(dict.fromkeys(
                tool for tool in enabled_tools if isinstance(tool, str)
            ))
            if not isinstance(self._values.get("auto_model"), bool):
                self._values["auto_model"] = True
            if not isinstance(self._values.get("memory_enabled"), bool):
                self._values["memory_enabled"] = True
            return dict(self._values)

    def get(self, key, default=None):
        with self._lock:
            return self._values.get(key, default)

    def update(self, **changes):
        with self._lock:
            self._values.update(changes)
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temporary = self.path.with_suffix(self.path.suffix + ".tmp")
            temporary.write_text(
                json.dumps(self._values, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            temporary.replace(self.path)
            return dict(self._values)
