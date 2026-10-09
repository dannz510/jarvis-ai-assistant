from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field


class MsgIn(BaseModel):
    role: str = Field(pattern=r"^(user|assistant|tool|system|thought)$")
    content: str
    tokens_in: Optional[int] = 0
    tokens_out: Optional[int] = 0
    latency_ms: Optional[float] = 0.0
    model: Optional[str] = ""
    tool_calls: Optional[List[dict]] = Field(default_factory=list)
    tool_results: Optional[List[dict]] = Field(default_factory=list)


class MsgOut(BaseModel):
    id: int
    session_id: int
    role: str
    content: str
    tokens_in: int
    tokens_out: int
    latency_ms: float
    model: str
    created_at: str
    tool_calls: List[dict] = Field(default_factory=list)
    tool_results: List[dict] = Field(default_factory=list)


class SessionOut(BaseModel):
    id: int
    uuid: str
    user_id: Optional[int]
    title: str
    state: str
    model: str
    agent: str
    started_at: Optional[str]
    ended_at: Optional[str]
    tokens_in: int
    tokens_out: int
    total_tokens: int
