"""Persistent task execution context for multi-turn local workflows."""

from contextlib import contextmanager
import json
import os
from pathlib import Path
import re
import sqlite3
import threading
import time
from uuid import uuid4


_SENSITIVE = re.compile(
    r"(?:\b(password|passphrase|api[_ -]?key|access[_ -]?token|secret|credit card|cvv|ssn|"
    r"bank account|private key|recovery code)\b|"
    r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b|"
    r"(?<!\d)(?:\+?\d[\s().-]?){9,}(?!\d))",
    re.I,
)
_FREEFORM_ENTRY = re.compile(r"^(?:set text in control|nhập văn bản vào điều khiển)\b", re.I)


class TaskStore:
    """SQLite-backed task state. Sensitive text is rejected before persistence."""

    def __init__(self, database_path):
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._initialize()

    @contextmanager
    def _connect(self):
        connection = sqlite3.connect(str(self.database_path), timeout=5)
        connection.row_factory = sqlite3.Row
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def _initialize(self):
        with self._connect() as connection:
            connection.execute(
                """CREATE TABLE IF NOT EXISTS tasks (
                    task_id TEXT PRIMARY KEY,
                    goal TEXT NOT NULL,
                    status TEXT NOT NULL,
                    current_step TEXT NOT NULL DEFAULT '',
                    active_application TEXT NOT NULL DEFAULT '',
                    active_file TEXT NOT NULL DEFAULT '',
                    last_observation TEXT NOT NULL DEFAULT '',
                    completed_steps TEXT NOT NULL DEFAULT '[]',
                    pending_steps TEXT NOT NULL DEFAULT '[]',
                    artifacts TEXT NOT NULL DEFAULT '[]',
                    errors TEXT NOT NULL DEFAULT '[]',
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                )"""
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_astra_tasks_updated ON tasks(updated_at DESC)"
            )

    @staticmethod
    def _safe(value, limit=1200):
        text = str(value or "").strip()
        if not text or _SENSITIVE.search(text) or _FREEFORM_ENTRY.search(text):
            return ""
        return text[:limit]

    @staticmethod
    def _loads(value):
        try:
            result = json.loads(value or "[]")
            return result if isinstance(result, list) else []
        except (TypeError, json.JSONDecodeError):
            return []

    @staticmethod
    def _as_task(row):
        if row is None:
            return None
        task = dict(row)
        for field in ("completed_steps", "pending_steps", "artifacts", "errors"):
            task[field] = TaskStore._loads(task.get(field))
        return task

    def latest(self):
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM tasks ORDER BY updated_at DESC LIMIT 1"
            ).fetchone()
        return self._as_task(row)

    def get_active(self):
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM tasks WHERE status = 'active' ORDER BY updated_at DESC LIMIT 1"
            ).fetchone()
        return self._as_task(row)

    def list_recent(self, limit=50):
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM tasks ORDER BY updated_at DESC LIMIT ?",
                (max(1, min(200, int(limit))),),
            ).fetchall()
        return [self._as_task(row) for row in rows]

    def begin(self, goal, follow_up=False, active_application="", active_file=""):
        safe_goal = self._safe(goal)
        if not safe_goal:
            return None
        now = time.time()
        with self._lock, self._connect() as connection:
            previous = connection.execute(
                "SELECT * FROM tasks ORDER BY updated_at DESC LIMIT 1"
            ).fetchone()
            if follow_up and previous and now - previous["updated_at"] <= 86400:
                task_id = previous["task_id"]
                pending = self._loads(previous["pending_steps"])
                pending.append(safe_goal)
                connection.execute(
                    """UPDATE tasks SET status='active', current_step=?, active_application=?,
                       active_file=?, pending_steps=?, updated_at=? WHERE task_id=?""",
                    (safe_goal, self._safe(active_application, 240), self._safe(active_file, 1200),
                     json.dumps(pending[-30:], ensure_ascii=False), now, task_id),
                )
                return task_id

            if previous and previous["status"] == "active":
                connection.execute(
                    "UPDATE tasks SET status='paused', updated_at=? WHERE task_id=?",
                    (now, previous["task_id"]),
                )
            task_id = uuid4().hex
            connection.execute(
                """INSERT INTO tasks (
                    task_id, goal, status, current_step, active_application, active_file,
                    pending_steps, created_at, updated_at
                ) VALUES (?, ?, 'active', ?, ?, ?, ?, ?, ?)""",
                (task_id, safe_goal, safe_goal, self._safe(active_application, 240),
                 self._safe(active_file, 1200), json.dumps([safe_goal], ensure_ascii=False), now, now),
            )
            return task_id

    def observe(self, task_id, observation, current_step=""):
        safe_observation = self._safe(observation)
        safe_step = self._safe(current_step, 500)
        if not task_id or not safe_observation:
            return False
        with self._connect() as connection:
            cursor = connection.execute(
                "UPDATE tasks SET last_observation=?, current_step=COALESCE(NULLIF(?, ''), current_step), updated_at=? WHERE task_id=?",
                (safe_observation, safe_step, time.time(), task_id),
            )
            return cursor.rowcount > 0

    def complete_step(self, task_id, step, observation=""):
        safe_step = self._safe(step, 500)
        safe_observation = self._safe(observation)
        if not task_id or not safe_step:
            return False
        with self._lock, self._connect() as connection:
            row = connection.execute(
                "SELECT completed_steps, pending_steps FROM tasks WHERE task_id=?", (task_id,)
            ).fetchone()
            if row is None:
                return False
            completed = self._loads(row["completed_steps"])
            pending = self._loads(row["pending_steps"])
            if safe_step in pending:
                pending.remove(safe_step)
            completed.append({"step": safe_step, "result": safe_observation, "at": time.time()})
            connection.execute(
                """UPDATE tasks SET completed_steps=?, pending_steps=?, current_step='',
                   last_observation=?, updated_at=? WHERE task_id=?""",
                (json.dumps(completed[-50:], ensure_ascii=False),
                 json.dumps(pending[-30:], ensure_ascii=False), safe_observation,
                 time.time(), task_id),
            )
            return True

    def add_error(self, task_id, error):
        safe_error = self._safe(error, 500)
        if not task_id or not safe_error:
            return False
        with self._lock, self._connect() as connection:
            row = connection.execute("SELECT errors FROM tasks WHERE task_id=?", (task_id,)).fetchone()
            if row is None:
                return False
            errors = self._loads(row["errors"])
            errors.append({"error": safe_error, "at": time.time()})
            connection.execute(
                "UPDATE tasks SET errors=?, status='failed', updated_at=? WHERE task_id=?",
                (json.dumps(errors[-30:], ensure_ascii=False), time.time(), task_id),
            )
            return True

    def add_artifact(self, task_id, artifact):
        safe_artifact = self._safe(artifact, 1200)
        if not task_id or not safe_artifact:
            return False
        with self._lock, self._connect() as connection:
            row = connection.execute("SELECT artifacts FROM tasks WHERE task_id=?", (task_id,)).fetchone()
            if row is None:
                return False
            artifacts = self._loads(row["artifacts"])
            if safe_artifact not in artifacts:
                artifacts.append(safe_artifact)
            connection.execute(
                "UPDATE tasks SET artifacts=?, updated_at=? WHERE task_id=?",
                (json.dumps(artifacts[-50:], ensure_ascii=False), time.time(), task_id),
            )
            return True

    def finish(self, task_id, status="completed"):
        if status not in {"active", "paused", "completed", "failed"}:
            raise ValueError("Invalid task status.")
        if not task_id:
            return False
        with self._connect() as connection:
            cursor = connection.execute(
                "UPDATE tasks SET status=?, updated_at=? WHERE task_id=?",
                (status, time.time(), task_id),
            )
            return cursor.rowcount > 0

