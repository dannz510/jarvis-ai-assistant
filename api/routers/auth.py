from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from api.deps import require_localhost

router = APIRouter(dependencies=[Depends(require_localhost)])


@router.get("/me")
def me():
    return {"username": "default", "roles": ["admin"]}


@router.post("/session")
def create_session():
    return {"ok": True}


@router.post("/logout")
def logout():
    return {"ok": True}
