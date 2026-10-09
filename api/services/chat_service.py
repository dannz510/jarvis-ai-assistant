from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import hashlib
import json
import re

from core.config import get_config
from core.db.session import session_scope
from core.models.entities import Message, Session, User

from Security import audit
from Security.redaction import redact_text as security_redact_text


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


_SENSITIVE = re.compile(
    r"(?:\b(password|passphrase|api[_ -]?key|access[_ -]?token|secret)\b|"
    r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b|"
    r"(?<!\d)(?:\+?\d[\s().-]?){9,}(?!\d))",
    re.I,
)


def redact_text(s: str) -> str:
    if not s:
        return s
    return _SENSITIVE.sub("[REDACTED]", s)


def get_or_create_user(username: str = "default") -> User:
    with session_scope() as s:
        u = s.query(User).filter(User.username == username).first()
        if u:
            return u
        u = User(username=username, display_name=username)
        s.add(u)
        s.flush()
        return u


def list_sessions(user_id: Optional[int] = None, limit: int = 50) -> List[Dict[str, Any]]:
    with session_scope() as s:
        q = s.query(Session)
        if user_id:
            q = q.filter(Session.user_id == user_id)
        q = q.order_by(Session.started_at.desc()).limit(limit)
        res = []
        for r in q:
            res.append(
                {
                    "id": r.id,
                    "uuid": r.uuid,
                    "user_id": r.user_id,
                    "title": r.title,
                    "state": r.state,
                    "model": r.model,
                    "agent": r.agent,
                    "started_at": r.started_at.isoformat() if r.started_at else None,
                    "ended_at": r.ended_at.isoformat() if r.ended_at else None,
                    "tokens_in": r.tokens_in,
                    "tokens_out": r.tokens_out,
                    "total_tokens": r.total_tokens,
                }
            )
        return res


def get_session(session_id: int) -> Optional[Dict[str, Any]]:
    with session_scope() as s:
        r = s.query(Session).get(session_id)
        if not r:
            return None
        return {
            "id": r.id,
            "uuid": r.uuid,
            "user_id": r.user_id,
            "title": r.title,
            "state": r.state,
            "model": r.model,
            "agent": r.agent,
            "started_at": r.started_at.isoformat() if r.started_at else None,
            "ended_at": r.ended_at.isoformat() if r.ended_at else None,
        }


def list_messages(session_id: int, limit: int = 200) -> List[Dict[str, Any]]:
    with session_scope() as s:
        q = s.query(Message).filter(Message.session_id == session_id).order_by(Message.created_at.asc()).limit(limit)
        res = []
        for r in q:
            res.append(
                {
                    "id": r.id,
                    "session_id": r.session_id,
                    "role": r.role,
                    "content": security_redact_text(r.content),
                    "tool_calls": r.tool_calls_list(),
                    "tool_results": r.tool_results_list(),
                    "tokens_in": r.tokens_in,
                    "tokens_out": r.tokens_out,
                    "latency_ms": r.latency_ms,
                    "model": r.model,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
            )
        return res


def append_message(session_id: int, role: str, content: str, **kw) -> int:
    cfg = get_config()
    h = hashlib.sha256(f"{session_id}:{role}:{content}".encode("utf-8")).hexdigest()
    with session_scope() as s:
        m = Message(
            session_id=session_id,
            role=role,
            content=security_redact_text(content) if cfg.pii_redaction else content,
            hash=h,
            tool_calls=json.dumps(kw.get("tool_calls") or [], ensure_ascii=False),
            tool_results=json.dumps(kw.get("tool_results") or [], ensure_ascii=False),
            tokens_in=int(kw.get("tokens_in") or 0),
            tokens_out=int(kw.get("tokens_out") or 0),
            latency_ms=float(kw.get("latency_ms") or 0.0),
            model=kw.get("model") or "",
        )
        s.add(m)
        s.flush()
        audit.AuditLogger().log(action="chat.message.append", resource_type="message", resource_id=str(m.id), result="ok")
        return m.id



