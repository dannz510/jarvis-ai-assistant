from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from core.db.session import session_scope
from core.models.telemetry_storage_audit import AuditLog


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AuditLogger:
    def __init__(self) -> None:
        pass

    def log(
        self,
        *,
        actor_id: Optional[int] = None,
        actor_type: str = "user",
        action: str = "action",
        resource_type: str = "",
        resource_id: str = "",
        ip: str = "",
        user_agent: str = "",
        meta: Optional[Dict[str, Any]] = None,
        result: str = "ok",
        trace_id: Optional[str] = None,
    ) -> int:
        tid = trace_id or str(uuid.uuid4())
        m = json.dumps(meta or {}, ensure_ascii=False)
        with session_scope() as s:
            al = AuditLog(
                actor_id=actor_id,
                actor_type=actor_type,
                action=action,
                resource_type=resource_type,
                resource_id=str(resource_id or ""),
                ip=ip,
                user_agent=user_agent[:255],
                meta=m,
                result=result,
                trace_id=tid,
                immutable=True,
            )
            s.add(al)
            s.flush()
            return al.id

    def list_audit(self, limit: int = 100, action: Optional[str] = None, actor_id: Optional[int] = None) -> list[Dict[str, Any]]:
        with session_scope() as s:
            q = s.query(AuditLog).order_by(AuditLog.ts.desc())
            if action:
                q = q.filter(AuditLog.action == action)
            if actor_id is not None:
                q = q.filter(AuditLog.actor_id == actor_id)
            rows = q.limit(min(limit, 500)).all()
            out: list[Dict[str, Any]] = []
            for r in rows:
                out.append(
                    {
                        "id": r.id,
                        "ts": r.ts.isoformat() if r.ts else None,
                        "actor_id": r.actor_id,
                        "actor_type": r.actor_type,
                        "action": r.action,
                        "resource_type": r.resource_type,
                        "resource_id": r.resource_id,
                        "ip": r.ip,
                        "user_agent": r.user_agent,
                        "meta": r.meta_dict(),
                        "result": r.result,
                        "trace_id": r.trace_id,
                        "immutable": r.immutable,
                    }
                )
            return out
