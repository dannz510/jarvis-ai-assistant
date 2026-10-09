from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from api.services.chat_service import (
    get_or_create_user,
    list_sessions,
    get_session,
    list_messages,
    append_message,
)
from storage.manager import StorageManager
from metrics.charts import Charts
from metrics.collector import MetricsCollector
from api.deps import require_localhost
from core.schemas.chat import MsgIn

router = APIRouter(dependencies=[Depends(require_localhost)])


@router.get("/sessions")
def sessions(user_id: Optional[int] = Query(None)):
    return {"sessions": list_sessions(user_id)}


@router.get("/sessions/{session_id}")
def session(session_id: int):
    s = get_session(session_id)
    if not s:
        raise HTTPException(404, "session not found")
    return s


@router.get("/sessions/{session_id}/messages")
def messages(session_id: int, limit: int = Query(200, ge=1, le=500)):
    return {"messages": list_messages(session_id, limit)}


@router.post("/sessions/{session_id}/messages")
def add_message(session_id: int, body: MsgIn):
    mid = append_message(
        session_id,
        role=body.role,
        content=body.content,
        tokens_in=body.tokens_in,
        tokens_out=body.tokens_out,
        latency_ms=body.latency_ms,
        model=body.model,
    )
    MetricsCollector().record(op="chat", session_id=session_id, tokens_in=body.tokens_in or 0, tokens_out=body.tokens_out or 0)
    return {"id": mid}


@router.get("/health")
def health():
    return {"status": "ok"}
