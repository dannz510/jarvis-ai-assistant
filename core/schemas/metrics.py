from __future__ import annotations

from typing import List
from pydantic import BaseModel


class SeriesQuery(BaseModel):
    metric: str = "events"
    interval: str = "1h"
    from_ts: str | None = None
    to_ts: str | None = None
    user_id: int | None = None
    session_id: int | None = None
