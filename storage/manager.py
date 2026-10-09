from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from core.config import get_config
from core.db.session import session_scope
from core.models.telemetry_storage_audit import StorageObject, Quota
from storage.crypto import CryptoManager


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class StorageManager:
    """Quản lý storage: overview, breakdown, quotas, lifecycle, retention, purge (local-first)."""

    def __init__(self) -> None:
        self.cfg = get_config()
        self.cfg.ensure_dirs()
        self.crypto = CryptoManager()

    def get_overview(self) -> Dict[str, Any]:
        total_bytes = 0
        total_files = 0
        by_mime: Dict[str, int] = {}
        by_scope: Dict[str, int] = {}
        for p in self.cfg.storage_dir.rglob("*"):
            if p.is_file():
                try:
                    st = p.stat()
                    total_bytes += st.st_size
                    total_files += 1
                except Exception:
                    pass
        used_pct = (total_bytes / self.cfg.max_storage_bytes * 100.0) if self.cfg.max_storage_bytes > 0 else 0.0
        return {
            "storage_dir": str(self.cfg.storage_dir),
            "total_bytes": total_bytes,
            "total_files": total_files,
            "max_bytes": self.cfg.max_storage_bytes,
            "used_pct": round(used_pct, 2),
            "by_mime": by_mime,
            "by_scope": by_scope,
        }

    def get_tree(self, limit: int = 200) -> List[Dict[str, Any]]:
        items: List[Dict[str, Any]] = []
        for p in sorted(self.cfg.storage_dir.rglob("*")):
            try:
                rel = p.relative_to(self.cfg.storage_dir)
            except Exception:
                continue
            if len(items) >= limit:
                break
            items.append(
                {
                    "path": str(p),
                    "rel_path": str(rel).replace("\\", "/"),
                    "is_dir": p.is_dir(),
                    "size_bytes": p.stat().st_size if p.is_file() else 0,
                    "name": p.name,
                }
            )
        return items

    def get_breakdown(self) -> Dict[str, Any]:
        return self.get_overview()

    def enforce_quotas(self) -> Dict[str, Any]:
        with session_scope() as s:
            rows = s.query(Quota).all()
            return {
                "count": len(rows),
                "items": [
                    {
                        "scope": r.scope,
                        "owner_id": r.owner_id,
                        "quota_type": r.quota_type,
                        "limit_bytes": r.limit_bytes,
                        "limit_count": r.limit_count,
                        "used_bytes": r.used_bytes,
                        "used_count": r.used_count,
                        "warn_at_pct": r.warn_at_pct,
                        "hard_at_pct": r.hard_at_pct,
                    }
                    for r in rows
                ],
            }

    def retention_apply(self, days_chat: Optional[int] = None, days_metrics: Optional[int] = None) -> Dict[str, Any]:
        days_chat = days_chat or self.cfg.retention_days_chat
        days_metrics = days_metrics or self.cfg.retention_days_metrics
        now = utcnow()
        cutoff_chat = now - timedelta(days=days_chat)
        cutoff_metrics = now - timedelta(days=days_metrics)
        deleted_chat = 0
        deleted_metrics = 0
        from core.models.entities import Message
        from core.models.telemetry_storage_audit import UsageMetric

        with session_scope() as s:
            deleted_chat = s.query(Message).filter(Message.created_at < cutoff_chat).delete(synchronize_session=False)
            deleted_metrics = s.query(UsageMetric).filter(UsageMetric.ts < cutoff_metrics).delete(synchronize_session=False)
        return {
            "cutoff_chat": cutoff_chat.isoformat(),
            "cutoff_metrics": cutoff_metrics.isoformat(),
            "deleted_chat": int(deleted_chat),
            "deleted_metrics": int(deleted_metrics),
        }

    def purge_expired(self) -> Dict[str, Any]:
        purged = 0
        now = utcnow()
        with session_scope() as s:
            objs = s.query(StorageObject).filter(StorageObject.deleted_at.isnot(None), StorageObject.purged.is_(False)).all()
            for o in objs:
                try:
                    p = Path(o.path)
                    if p.exists():
                        p.unlink(missing_ok=True)
                    o.purged = True
                    purged += 1
                except Exception:
                    continue
        return {"purged": purged, "ts": now.isoformat()}
