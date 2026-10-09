from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, LargeBinary, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.models.base import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class UsageMetric(Base):
    __tablename__ = "usage_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    session_id: Mapped[Optional[int]] = mapped_column(ForeignKey("sessions.id", ondelete="SET NULL"), nullable=True)
    op: Mapped[str] = mapped_column(String(32), default="unknown")
    namespace: Mapped[str] = mapped_column(String(32), default="default")
    bytes_in: Mapped[int] = mapped_column(Integer, default=0)
    bytes_out: Mapped[int] = mapped_column(Integer, default=0)
    tokens_in: Mapped[int] = mapped_column(Integer, default=0)
    tokens_out: Mapped[int] = mapped_column(Integer, default=0)
    duration_ms: Mapped[float] = mapped_column(Float, default=0.0)
    cache_hit: Mapped[bool] = mapped_column(Boolean, default=False)
    hit_ratio: Mapped[float] = mapped_column(Float, default=0.0)
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    latency_ms: Mapped[float] = mapped_column(Float, default=0.0)

    __table_args__ = (
        Index("ix_usage_ts_user", "ts", "user_id"),
        Index("ix_usage_ts_session", "ts", "session_id"),
        Index("ix_usage_ts_op", "ts", "op"),
    )


class StorageObject(Base):
    __tablename__ = "storage_objects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    uuid: Mapped[str] = mapped_column(String(36), unique=True, default=lambda: str(uuid.uuid4()))
    owner_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    scope: Mapped[str] = mapped_column(String(32), default="user")  # user/system
    path: Mapped[str] = mapped_column(Text, nullable=False)
    rel_path: Mapped[str] = mapped_column(Text, default="")
    sha256: Mapped[str] = mapped_column(String(64), default="")
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    mime: Mapped[str] = mapped_column(String(128), default="application/octet-stream")
    encrypted: Mapped[bool] = mapped_column(Boolean, default=True)
    key_id: Mapped[str] = mapped_column(String(64), default="")
    retention_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    lifecycle_state: Mapped[str] = mapped_column(String(16), default="hot")  # hot/warm/cold/archive
    last_accessed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    access_count: Mapped[int] = mapped_column(Integer, default=0)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    purged: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    owner: Mapped[Optional["User"]] = relationship(back_populates="storage_objects")

    __table_args__ = (
        Index("ix_storage_owner_scope", "owner_id", "scope"),
        Index("ix_storage_created", "created_at"),
        Index("ix_storage_deleted_purged", "deleted_at", "purged"),
    )


class CacheEntry(Base):
    __tablename__ = "cache_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    namespace: Mapped[str] = mapped_column(String(32), nullable=False)
    key: Mapped[str] = mapped_column(String(512), nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), default="")
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    hits: Mapped[int] = mapped_column(Integer, default=0)
    misses: Mapped[int] = mapped_column(Integer, default=0)
    ttl_s: Mapped[int] = mapped_column(Integer, default=300)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    accessed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    evicted: Mapped[bool] = mapped_column(Boolean, default=False)
    evicted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    reason: Mapped[str] = mapped_column(String(64), default="")

    __table_args__ = (
        Index("ix_cache_ns_key", "namespace", "key"),
        Index("ix_cache_expires", "expires_at"),
        Index("ix_cache_accessed", "accessed_at"),
        Index("ix_cache_evicted", "evicted"),
    )


class Quota(Base):
    __tablename__ = "quotas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    scope: Mapped[str] = mapped_column(String(32), nullable=False)  # user/system
    owner_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    quota_type: Mapped[str] = mapped_column(String(32), nullable=False)  # storage/cache/msgs/tokens
    limit_bytes: Mapped[int] = mapped_column(Integer, default=0)
    limit_count: Mapped[int] = mapped_column(Integer, default=0)
    used_bytes: Mapped[int] = mapped_column(Integer, default=0)
    used_count: Mapped[int] = mapped_column(Integer, default=0)
    warn_at_pct: Mapped[int] = mapped_column(Integer, default=70)
    hard_at_pct: Mapped[int] = mapped_column(Integer, default=95)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    __table_args__ = (
        Index("ix_quotas_scope_owner_type", "scope", "owner_id", "quota_type"),
    )


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    actor_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    actor_type: Mapped[str] = mapped_column(String(16), default="user")
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(32), default="")
    resource_id: Mapped[str] = mapped_column(String(64), default="")
    ip: Mapped[str] = mapped_column(String(45), default="")
    user_agent: Mapped[str] = mapped_column(String(255), default="")
    meta: Mapped[str] = mapped_column(Text, default="{}")  # JSON
    result: Mapped[str] = mapped_column(String(8), default="ok")  # ok/fail
    trace_id: Mapped[str] = mapped_column(String(36), default="")
    immutable: Mapped[bool] = mapped_column(Boolean, default=True)

    __table_args__ = (
        Index("ix_audit_ts_actor", "ts", "actor_id"),
        Index("ix_audit_action_ts", "action", "ts"),
    )

    def meta_dict(self) -> dict:
        try:
            return json.loads(self.meta)
        except Exception:
            return {}
