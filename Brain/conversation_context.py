"""Short-term and working context for follow-up requests."""

from collections import deque
from dataclasses import dataclass, field
import re
import threading


_APPLICATIONS = {
    "excel": "Microsoft Excel",
    "word": "Microsoft Word",
    "powerpoint": "Microsoft PowerPoint",
    "chrome": "Google Chrome",
    "edge": "Microsoft Edge",
    "vscode": "Visual Studio Code",
    "vs code": "Visual Studio Code",
    "file explorer": "File Explorer",
}
_REFERENCES = re.compile(
    r"\b(this|that|these|those)\b|\b(?:open|save|rename|format|edit|delete|read|summarize|move|copy|change)\s+it\b|"
    r"\bwhat(?:'s| is) in it\b|nó|cái này|cái đó|file đó|app vừa mở|bảng trên|đoạn thứ hai|cái lúc nãy|phần này",
    re.I,
)
_FOLLOWUP_ACTION = re.compile(
    r"^(?:and\s+)?(?:also\s+|then\s+|now\s+)?(?:create|make|add|insert|format|edit|change|save|calculate|sort|filter|chart|summari[sz]e|tạo|làm|thêm|chèn|định dạng|chỉnh|sửa|lưu|tính|sắp xếp|lọc|vẽ|tóm tắt)\b",
    re.I,
)
_APP_LAUNCH = re.compile(r"\b(?:open|launch|switch|mở|chạy)\b", re.I)


@dataclass
class WorkingContext:
    active_app: str = ""
    active_file: str = ""
    active_task: str = ""
    active_topic: str = ""
    recent_entities: list[str] = field(default_factory=list)
    recent_actions: list[str] = field(default_factory=list)


class ConversationContext:
    """Bounded turn history plus lightweight application/file working state."""

    def __init__(self, max_turns=8):
        self._turns = deque(maxlen=max_turns)
        self.working = WorkingContext()
        self._lock = threading.RLock()

    def add_user(self, text):
        text = str(text).strip()
        if not text:
            return
        lowered = text.casefold()
        with self._lock:
            self._turns.append(("User", text))
            self.working.active_topic = text[:240]
            if not _REFERENCES.search(text):
                self.working.active_task = text[:240]
            for token, app_name in _APPLICATIONS.items():
                if token in lowered and any(verb in lowered for verb in ("open", "launch", "switch", "mở", "chạy")):
                    self.working.active_app = app_name
                    self.working.recent_actions.append(f"open {app_name}")
                    self.working.recent_actions = self.working.recent_actions[-6:]
            path_match = re.search(r"(?:[a-z]:\\|\\\\)[^\r\n\"<>|?*]+", text, re.I)
            if path_match:
                self.working.active_file = path_match.group(0).strip().rstrip(".,;:")
                self.working.recent_entities.append(self.working.active_file)
                self.working.recent_entities = self.working.recent_entities[-12:]

    def add_assistant(self, text):
        if text:
            with self._lock:
                self._turns.append(("ASTRA", str(text).strip()))

    def is_follow_up(self, text):
        text = str(text or "").strip()
        with self._lock:
            if not self.working.active_task:
                return False
            if _REFERENCES.search(text):
                return True
            if _APP_LAUNCH.search(text):
                return False
            return bool(self.working.active_app and _FOLLOWUP_ACTION.search(text))

    def restore_working(self, active_app="", active_file="", active_task=""):
        with self._lock:
            self.working.active_app = str(active_app or "")
            self.working.active_file = str(active_file or "")
            self.working.active_task = str(active_task or "")

    def recent_turns(self, count=8):
        with self._lock:
            return list(self._turns)[-count:]

    def context_for(self, prompt):
        with self._lock:
            parts = []
            if _REFERENCES.search(prompt):
                if self.working.active_app:
                    parts.append(f"Current application: {self.working.active_app}.")
                if self.working.active_file:
                    parts.append(f"Current file: {self.working.active_file}.")
                if self.working.active_task:
                    parts.append(f"Active task/topic: {self.working.active_task}.")
            elif self.working.active_app:
                parts.append(f"Current application: {self.working.active_app}.")
            return "\n".join(parts)
