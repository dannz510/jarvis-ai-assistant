from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from core.config import get_config
from storage.manager import StorageManager


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class RetentionPolicy:
    days_chat: int = 90
    days_metrics: int = 365
    days_audit: int = 3650

    def apply(self, sm: Optional[StorageManager] = None) -> Dict[str, Any]:
        sm = sm or StorageManager()
        return sm.retention_apply(self.days_chat, self.days_metrics)


@dataclass
class LifecyclePolicy:
    auto_purge_expired: bool = True

    def apply(self, sm: Optional[StorageManager] = None) -> Dict[str, Any]:
        sm = sm or StorageManager()
        res: Dict[str, Any] = {}
        if self.auto_purge_expired:
            res["purge"] = sm.purge_expired()
        return res


class PolicyOrchestrator:
    def __init__(self, cfg=None) -> None:
        self.cfg = cfg or get_config()
        self.retention = RetentionPolicy(
            days_chat=self.cfg.retention_days_chat,
            days_metrics=self.cfg.retention_days_metrics,
            days_audit=self.cfg.retention_days_audit,
        )
        self.lifecycle = LifecyclePolicy()

    def apply_all(self) -> Dict[str, Any]:
        sm = StorageManager()
        return {"retention": self.retention.apply(sm), "lifecycle": self.lifecycle.apply(sm), "ts": utcnow().isoformat()}
