from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from Security import audit

from metrics.charts import Charts
from api.deps import require_localhost
from metrics.collector import MetricsAggregator

router = APIRouter(dependencies=[Depends(require_localhost)])
charts = Charts()
aggr = MetricsAggregator()


@router.get("/series")
def series(metric: str = Query("events"), interval: str = Query("1h"), from_ts: Optional[str] = Query(None), to_ts: Optional[str] = Query(None)):
    from datetime import datetime

    def p(s):
        if not s:
            return None
        try:
            return datetime.fromisoformat(s.replace("Z", "+00:00"))
        except Exception:
            return None

    result = aggr.series(metric=metric, interval=interval, from_ts=p(from_ts), to_ts=p(to_ts))
    audit.log("metrics.series.read", {"metric": metric, "interval": interval})
    return result


@router.get("/charts/usage")
def chart_usage(interval: str = Query("1h")):
    result = charts.usage_over_time(interval=interval)
    audit.log("metrics.chart.usage", {"interval": interval})
    return result


@router.get("/charts/tokens")
def chart_tokens(interval: str = Query("1h")):
    result = charts.tokens_over_time(interval=interval)
    audit.log("metrics.chart.tokens", {"interval": interval})
    return result


@router.get("/charts/duration")
def chart_duration(interval: str = Query("1h")):
    result = charts.duration_over_time(interval=interval)
    audit.log("metrics.chart.duration", {"interval": interval})
    return result


@router.get("/charts/cache")
def chart_cache(interval: str = Query("1h")):
    result = charts.cache_hit_ratio(interval=interval)
    audit.log("metrics.chart.cache", {"interval": interval})
    return result


@router.get("/charts/storage")
def chart_storage():
    result = charts.storage_growth()
    audit.log("metrics.chart.storage", {})
    return result


@router.get("/charts/ops")
def chart_ops():
    result = charts.ops_distribution()
    audit.log("metrics.chart.ops", {})
    return result


@router.get("/health")
def health():
    return {"status": "ok"}
