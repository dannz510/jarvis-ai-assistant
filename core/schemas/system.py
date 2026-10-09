from __future__ import annotations

from typing import Any, Dict
from pydantic import BaseModel


class SystemInfo(BaseModel):
    local_only: bool
    web_host: str
    web_port: int
    storage_dir: str
    db_path: str
