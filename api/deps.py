from __future__ import annotations

from typing import Optional

from fastapi import Depends, Header, HTTPException, Request

from core.config import get_config


def require_localhost(request: Request):
    cfg = get_config()
    if cfg.local_only:
        ip = request.client.host if request.client else "unknown"
        if ip not in ("127.0.0.1", "::1", "localhost"):
            raise HTTPException(status_code=403, detail="Local-only mode: requests restricted to localhost")
    return True
