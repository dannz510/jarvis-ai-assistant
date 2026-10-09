from __future__ import annotations

from fastapi import APIRouter, Depends
from api.deps import require_localhost

router = APIRouter(dependencies=[Depends(require_localhost)])


@router.get("/")
def list_users():
    return {"items": []}


@router.post("/create")
def create_user():
    return {"ok": True}
