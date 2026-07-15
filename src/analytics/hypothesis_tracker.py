"""Track content/growth hypotheses and evaluate against traffic deltas."""
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional


@dataclass
class Hypothesis:
    date: str
    title: str
    description: str
    keywords: list
    metric: str
    baseline_value: float
    status: str = "running"


class HypothesisTracker:
    """
    Stores hypotheses with baselines.
    Each day, compares current metric to baseline and marks:
    - confirmed if delta > +threshold
    - rejected if delta < -threshold
    - inconclusive otherwise
    """

    def __init__(self, analytics: dict, threshold: float = 5.0):
        self.analytics = analytics
        self.threshold = threshold

    def archive_yesterday(self, traffic: dict) -> list:
        hypotheses = self.analytics.get("hypotheses", [])
        if not hypotheses:
            return []
        for h in hypotheses:
            if h.get("status") != "running":
                continue
            baseline = float(h.get("baseline_value", 0))
            current = float(traffic.get(h.get("metric", "page_views"), 0))
            h["evaluated_at"] = datetime.now(timezone.utc).isoformat()
            h["current_value"] = current
            if baseline > 0:
                delta = round((current - baseline) / baseline * 100, 1)
            else:
                delta = 0.0
            h["delta"] = delta
            if delta > self.threshold:
                h["status"] = "confirmed"
            elif delta < -self.threshold:
                h["status"] = "rejected"
            else:
                h["status"] = "inconclusive"
        return hypotheses

    def new_hypothesis(self, title: str, description: str, keywords: list, traffic: dict, metric: str = "page_views") -> dict:
        return {
            "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "title": title,
            "description": description,
            "keywords": keywords,
            "metric": metric,
            "baseline_value": float(traffic.get(metric, 0)),
            "status": "running",
        }
