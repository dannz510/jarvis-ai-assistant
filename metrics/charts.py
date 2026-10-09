from __future__ import annotations

from typing import Any, Dict, List, Optional

from metrics.collector import MetricsAggregator


def _chart_base(title: str, x_label: str = "Time", y_label: str = "Value") -> Dict[str, Any]:
    return {
        "type": "line",
        "data": {"labels": [], "datasets": []},
        "options": {
            "responsive": True,
            "plugins": {"title": {"display": True, "text": title}},
            "scales": {
                "x": {"title": {"display": True, "text": x_label}},
                "y": {"title": {"display": True, "text": y_label}},
            },
        },
    }


class Charts:
    def __init__(self) -> None:
        self.aggr = MetricsAggregator()

    def usage_over_time(self, interval: str = "1h", **kw) -> Dict[str, Any]:
        s = self.aggr.series(metric="events", interval=interval, **kw)
        spec = _chart_base("App usage over time", "Time", "Events")
        spec["type"] = "line"
        spec["data"]["labels"] = s["labels"]
        spec["data"]["datasets"] = [
            {
                "label": "Events",
                "data": s["data"],
                "fill": True,
                "borderWidth": 2,
                "tension": 0.25,
            }
        ]
        return spec

    def tokens_over_time(self, interval: str = "1h", **kw) -> Dict[str, Any]:
        s = self.aggr.series(metric="tokens_total", interval=interval, **kw)
        spec = _chart_base("Tokens over time", "Time", "Tokens")
        spec["type"] = "line"
        spec["data"]["labels"] = s["labels"]
        spec["data"]["datasets"] = [
            {"label": "Total tokens", "data": s["data"], "fill": True, "tension": 0.25}
        ]
        return spec

    def duration_over_time(self, interval: str = "1h", **kw) -> Dict[str, Any]:
        s = self.aggr.series(metric="duration_ms", interval=interval, **kw)
        spec = _chart_base("Session duration (ms)", "Time", "ms")
        spec["type"] = "line"
        spec["data"]["labels"] = s["labels"]
        spec["data"]["datasets"] = [
            {"label": "Duration", "data": s["data"], "fill": True, "tension": 0.25}
        ]
        return spec

    def cache_hit_ratio(self, interval: str = "1h", **kw) -> Dict[str, Any]:
        s = self.aggr.series(metric="cache_hits", interval=interval, **kw)
        spec = _chart_base("Cache hits", "Time", "Hits")
        spec["type"] = "bar"
        spec["data"]["labels"] = s["labels"]
        spec["data"]["datasets"] = [{"label": "Hits", "data": s["data"]}]
        return spec

    def storage_growth(self) -> Dict[str, Any]:
        from storage.manager import StorageManager

        sm = StorageManager()
        ov = sm.get_overview()
        spec = {
            "type": "doughnut",
            "data": {
                "labels": ["Used", "Free (est)"],
                "datasets": [
                    {
                        "data": [
                            ov["total_bytes"],
                            max(0, ov["max_bytes"] - ov["total_bytes"]),
                        ]
                    }
                ],
            },
            "options": {"plugins": {"title": {"display": True, "text": "Storage usage"}}},
        }
        return spec

    def ops_distribution(self) -> Dict[str, Any]:
        spec = {
            "type": "pie",
            "data": {"labels": ["chat", "tools", "cache", "storage"], "datasets": [{"data": [60, 20, 12, 8]}]},
            "options": {"plugins": {"title": {"display": True, "text": "Ops distribution"}}},
        }
        return spec
