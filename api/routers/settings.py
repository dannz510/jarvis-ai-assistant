from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from api.deps import require_localhost

router = APIRouter(dependencies=[Depends(require_localhost)])


@router.get("/")
def list_settings():
    return {"items": []}


@router.post("/update")
def update_settings():
    return {"ok": True}
