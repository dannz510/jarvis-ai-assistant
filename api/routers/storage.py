from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from storage.manager import StorageManager
from metrics.charts import Charts
from api.deps import require_localhost
from core.schemas.storage import RetentionIn
from Security import audit

router = APIRouter(dependencies=[Depends(require_localhost)])


@router.get("/overview")
def overview():
    audit.AuditLogger().log(action="storage.overview.read", resource_type="storage", result="ok")
    return StorageManager().get_overview()


@router.get("/tree")
def tree(limit: int = Query(200, ge=1, le=1000)):
    audit.AuditLogger().log(action="storage.tree.read", resource_type="storage", result="ok")
    return {"items": StorageManager().get_tree(limit)}


@router.get("/breakdown")
def breakdown():
    audit.AuditLogger().log(action="storage.breakdown.read", resource_type="storage", result="ok")
    return StorageManager().get_breakdown()


@router.get("/quotas")
def quotas():
    audit.AuditLogger().log(action="storage.quotas.read", resource_type="storage", result="ok")
    return StorageManager().enforce_quotas()


@router.post("/retention/apply")
def retention_apply(body: RetentionIn | None = None):
    body = body or RetentionIn()
    audit.AuditLogger().log(action="storage.retention.apply", resource_type="storage", meta={"days_chat": body.days_chat, "days_metrics": body.days_metrics}, result="ok")
    return StorageManager().retention_apply(body.days_chat, body.days_metrics)


@router.post("/purge/expired")
def purge_expired():
    audit.AuditLogger().log(action="storage.purge.expired", resource_type="storage", result="ok")
    return StorageManager().purge_expired()
