"""Local episodic and semantic memory with optional Ollama vector search."""

from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import re
import sqlite3
import struct
import urllib.request
from contextlib import contextmanager


_WORD = re.compile(r"[\wÀ-ỹ]+", re.UNICODE)
_SENSITIVE = re.compile(
    r"(?:\b(password|passphrase|api[_ -]?key|access[_ -]?token|secret|credit card|cvv|ssn|"
    r"bank account|private key|recovery code)\b|"
    r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b|"
    r"(?<!\d)(?:\+?\d[\s().-]?){9,}(?!\d))",
    re.I,
)
_IMPORTANT_MARKERS = (
    "remember", "hãy nhớ", "ghi nhớ", "don't forget", "đừng quên",
    "i prefer", "my preference", "tôi thích", "tôi muốn", "sở thích",
)


class MemoryStore:
    """Small SQLite vector store; lexical scoring remains available offline."""

    def __init__(self, database_path, embedding_model=None, ollama_url=None):
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.embedding_model = embedding_model or os.environ.get("ASTRA_EMBEDDING_MODEL", "").strip()
        self.memory_policy = os.environ.get("ASTRA_MEMORY_POLICY", "explicit").strip().casefold()
        self.ollama_url = (ollama_url or os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")).rstrip("/")
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
                """CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    text TEXT NOT NULL,
                    category TEXT NOT NULL,
                    importance REAL NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL,
                    pinned INTEGER NOT NULL DEFAULT 0,
                    embedding BLOB,
                    embedding_model TEXT,
                    source TEXT NOT NULL DEFAULT 'user'
                )"""
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_memories_category_time "
                "ON memories(category, created_at DESC)"
            )

    def _embed(self, text):
        if not self.embedding_model:
            return None
        payload = json.dumps({"model": self.embedding_model, "input": text}).encode("utf-8")
        request = urllib.request.Request(
            f"{self.ollama_url}/api/embed",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=2.5) as response:
                data = json.loads(response.read().decode("utf-8"))
            vector = data.get("embeddings", [[]])[0]
            return tuple(float(value) for value in vector) if vector else None
        except Exception:
            return None

    @staticmethod
    def _pack(vector):
        if not vector:
            return None
        return struct.pack(f"<{len(vector)}f", *vector)

    @staticmethod
    def _unpack(blob):
        if not blob or len(blob) % 4:
            return None
        return struct.unpack(f"<{len(blob) // 4}f", blob)

    def add(self, text, category="episodic", importance=1, pinned=False, source="user"):
        text = str(text).strip()
        if not text or _SENSITIVE.search(text):
            return None
        vector = self._embed(text)
        created = datetime.now(timezone.utc).isoformat()
        with self._connect() as connection:
            cursor = connection.execute(
                """INSERT INTO memories
                   (text, category, importance, created_at, pinned, embedding, embedding_model, source)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (text, category, max(0.0, min(5.0, float(importance))), created,
                 int(bool(pinned)), self._pack(vector), self.embedding_model if vector else None, source),
            )
            return cursor.lastrowid

    def replace_profile(self, text):
        """Replace user-edited durable memory without retaining removed entries."""
        lines = [line.strip(" -*\t") for line in str(text).splitlines() if line.strip(" -*\t")]
        memories = [line for line in lines if line and not _SENSITIVE.search(line)]
        with self._connect() as connection:
            connection.execute("DELETE FROM memories WHERE source = 'memory_editor'")
        ids = []
        for line in memories:
            memory_id = self.add(line, category="semantic", importance=4, source="memory_editor")
            if memory_id:
                ids.append(memory_id)
        return ids

    def maybe_store_important_turn(self, prompt, answer):
        """Store only turns that explicitly ask to remember durable information."""
        prompt = str(prompt).strip()
        if not prompt or not answer:
            return None
        if self.memory_policy in {"ask", "ask_before_saving", "do_not_save", "disabled"}:
            return None
        if self.requires_confirmation(prompt):
            return self.add(prompt, category="semantic", importance=5, source="explicit_turn")
        return None

    @staticmethod
    def requires_confirmation(prompt):
        prompt = str(prompt or "").strip()
        lowered = prompt.casefold()
        return bool(prompt and not _SENSITIVE.search(prompt) and
                    any(marker in lowered for marker in _IMPORTANT_MARKERS))

    @staticmethod
    def _lexical_score(query, text):
        query_terms = {word.casefold() for word in _WORD.findall(query) if len(word) > 1}
        text_terms = {word.casefold() for word in _WORD.findall(text) if len(word) > 1}
        if not query_terms or not text_terms:
            return 0.0
        return len(query_terms & text_terms) / math.sqrt(len(query_terms) * len(text_terms))

    @staticmethod
    def _cosine(left, right):
        if not left or not right or len(left) != len(right):
            return None
        dot = sum(a * b for a, b in zip(left, right))
        norm_left = math.sqrt(sum(a * a for a in left))
        norm_right = math.sqrt(sum(b * b for b in right))
        return dot / (norm_left * norm_right) if norm_left and norm_right else None

    def retrieve(self, query, limit=3):
        query_vector = self._embed(query)
        with self._connect() as connection:
            rows = connection.execute("SELECT * FROM memories").fetchall()
        now = datetime.now(timezone.utc)
        ranked = []
        for row in rows:
            relevance = self._lexical_score(query, row["text"])
            stored_vector = self._unpack(row["embedding"])
            if (query_vector and stored_vector and
                    row["embedding_model"] == self.embedding_model):
                semantic = self._cosine(query_vector, stored_vector)
                if semantic is not None:
                    relevance = max(relevance, max(0.0, semantic))
            if relevance <= 0.05 and not row["pinned"]:
                continue
            try:
                age_days = max(0.0, (now - datetime.fromisoformat(row["created_at"])).total_seconds() / 86400)
            except (TypeError, ValueError):
                age_days = 365.0
            recency = 1.0 / (1.0 + age_days / 30.0)
            score = relevance * (1.0 + 0.06 * float(row["importance"]) + 0.04 * recency)
            score += 0.2 if row["pinned"] else 0
            ranked.append((score, row["text"], row["category"], row["created_at"]))
        ranked.sort(key=lambda item: item[0], reverse=True)
        return [
            {"text": text, "category": category, "created_at": created, "score": score}
            for score, text, category, created in ranked[:max(0, int(limit))]
            if score > 0
        ]

    def list_memories(self, category=None):
        with self._connect() as connection:
            if category:
                rows = connection.execute(
                    "SELECT id, text, category, importance, created_at, pinned FROM memories WHERE category = ? ORDER BY pinned DESC, importance DESC, created_at DESC",
                    (category,),
                ).fetchall()
            else:
                rows = connection.execute(
                    "SELECT id, text, category, importance, created_at, pinned FROM memories ORDER BY pinned DESC, importance DESC, created_at DESC"
                ).fetchall()
        return [dict(row) for row in rows]

    def delete(self, memory_id):
        with self._connect() as connection:
            cursor = connection.execute("DELETE FROM memories WHERE id = ?", (int(memory_id),))
            return cursor.rowcount > 0

    def set_pinned(self, memory_id, pinned=True):
        with self._connect() as connection:
            cursor = connection.execute(
                "UPDATE memories SET pinned = ? WHERE id = ?",
                (int(bool(pinned)), int(memory_id)),
            )
            return cursor.rowcount > 0

    def set_importance(self, memory_id, importance):
        value = max(0.0, min(5.0, float(importance)))
        with self._connect() as connection:
            cursor = connection.execute(
                "UPDATE memories SET importance = ? WHERE id = ?",
                (value, int(memory_id)),
            )
            return cursor.rowcount > 0

    def clear(self):
        with self._connect() as connection:
            connection.execute("DELETE FROM memories")
