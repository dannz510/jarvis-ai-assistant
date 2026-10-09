from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class StorageOverview(BaseModel):
    storage_dir: str
    total_bytes: int
    total_files: int
    max_bytes: int
    used_pct: float


class RetentionIn(BaseModel):
    days_chat: Optional[int] = None
    days_metrics: Optional[int] = None
