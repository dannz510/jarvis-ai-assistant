from __future__ import annotations

from fastapi import APIRouter, Depends

from Security.audit import AuditLogger
from core.config import get_config
from api.deps import require_localhost

router = APIRouter(dependencies=[Depends(require_localhost)])


@router.get("/health")
def health():
    return {"status": "ok", "service": "system"}


@router.get("/info")
def info():
    from core.config import get_config

    c = get_config()
    return {
        "local_only": c.local_only,
        "web_host": c.web_host,
        "web_port": c.web_port,
        "storage_dir": str(c.storage_dir),
        "db_path": str(c.db_path),
    }


@router.get("/audit")
def audit(limit: int = 50, action: str | None = None, actor_id: int | None = None):
    return {"items": AuditLogger().list_audit(limit=limit, action=action, actor_id=actor_id)}
