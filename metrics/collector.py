from __future__ import annotations

from typing import Any, Dict, List, Optional

from core.db.session import session_scope
from core.models.telemetry_storage_audit import UsageMetric
from datetime import datetime, timedelta, timezone


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _bucket(ts: datetime, interval: str) -> datetime:
    ts = ts.astimezone(timezone.utc)
    if interval == "5m":
        m = (ts.minute // 5) * 5
        return ts.replace(second=0, microsecond=0, minute=m)
    if interval == "1h":
        return ts.replace(second=0, microsecond=0, minute=0)
    if interval == "1d":
        return ts.replace(hour=0, minute=0, second=0, microsecond=0)
    if interval == "7d":
        d = ts - timedelta(days=ts.weekday())
        return d.replace(hour=0, minute=0, second=0, microsecond=0)
    if interval == "30d":
        return ts.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return ts.replace(second=0, microsecond=0)


class MetricsAggregator:
    def __init__(self) -> None:
        from core.config import get_config

        self.cfg = get_config()

    def series(
        self,
        *,
        metric: str = "events",
        interval: str = "1h",
        from_ts: Optional[datetime] = None,
        to_ts: Optional[datetime] = None,
        user_id: Optional[int] = None,
        session_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        to_ts = to_ts or utcnow()
        from_ts = from_ts or (to_ts - timedelta(days=7))
        labels: List[str] = []
        data: List[float] = []
        cur = _bucket(from_ts, interval)
        step = timedelta(minutes=5)
        if interval == "1h":
            step = timedelta(hours=1)
        elif interval == "1d":
            step = timedelta(days=1)
        elif interval == "7d":
            step = timedelta(days=7)
        elif interval == "30d":
            step = timedelta(days=30)
        elif interval == "5m":
            step = timedelta(minutes=5)
        rows_map: Dict[str, float] = {}
        with session_scope() as s:
            q = s.query(UsageMetric).filter(UsageMetric.ts >= from_ts, UsageMetric.ts < to_ts)
            if user_id is not None:
                q = q.filter(UsageMetric.user_id == user_id)
            if session_id is not None:
                q = q.filter(UsageMetric.session_id == session_id)
            for r in q:
                try:
                    b = _bucket(r.ts, interval).isoformat()
                except Exception:
                    continue
                if metric == "tokens_total":
                    rows_map[b] = rows_map.get(b, 0.0) + float(r.tokens_in + r.tokens_out)
                elif metric == "tokens_out":
                    rows_map[b] = rows_map.get(b, 0.0) + float(r.tokens_out)
                elif metric == "tokens_in":
                    rows_map[b] = rows_map.get(b, 0.0) + float(r.tokens_in)
                elif metric == "duration_ms":
                    rows_map[b] = rows_map.get(b, 0.0) + float(r.duration_ms)
                elif metric == "latency_ms":
                    rows_map[b] = rows_map.get(b, 0.0) + float(r.latency_ms)
                elif metric == "bytes":
                    rows_map[b] = rows_map.get(b, 0.0) + float(r.bytes_in + r.bytes_out)
                elif metric == "cache_hits":
                    rows_map[b] = rows_map.get(b, 0.0) + (1.0 if r.cache_hit else 0.0)
                else:
                    rows_map[b] = rows_map.get(b, 0.0) + 1.0
        while cur < to_ts:
            k = cur.isoformat()
            labels.append(k)
            data.append(round(float(rows_map.get(k, 0.0)), 4))
            cur += step
            if len(labels) > 2000:
                break
        return {"labels": labels, "data": data, "metric": metric, "interval": interval}


class MetricsCollector:
    def __init__(self) -> None:
        self.cfg = get_config()

    def record(
        self,
        *,
        op: str,
        session_id: int,
        tokens_in: int = 0,
        tokens_out: int = 0,
        duration_ms: int = 0,
        latency_ms: int = 0,
        bytes_in: int = 0,
        bytes_out: int = 0,
        cache_hit: bool = False,
        user_id: Optional[int] = None,
    ) -> None:
        with session_scope() as s:
            metric = UsageMetric(
                ts=utcnow(),
                user_id=user_id,
                session_id=session_id,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                duration_ms=duration_ms,
                latency_ms=latency_ms,
                bytes_in=bytes_in,
                bytes_out=bytes_out,
                cache_hit=cache_hit,
            )
            s.add(metric)
