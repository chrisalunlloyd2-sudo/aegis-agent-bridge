"""Rate repository and content metadata by activity, completeness, and health."""
import os
import re
from datetime import datetime, timezone
from typing import Optional


class MetadataRater:
    def __init__(self, repos_dir: Optional[str] = None):
        self.repos_dir = repos_dir

    def rate_repo(self, repo: dict) -> dict:
        """Rate a repo entry from data.json or GitHub API."""
        name = repo.get("name", "unknown")
        url = repo.get("url", "")
        readme = repo.get("readme", "")
        last_commit = repo.get("last_commit", "")
        has_tests = repo.get("has_tests", False)
        has_docs = repo.get("has_docs", False)
        open_issues = repo.get("open_issues", 0)

        score = 5.0
        reasons = []

        # Activity: recent commits add points
        if last_commit:
            try:
                dt = datetime.fromisoformat(last_commit.replace("Z", "+00:00"))
                days = (datetime.now(timezone.utc) - dt).days
                if days < 7:
                    score += 2.0
                    reasons.append("active (last commit <7d)")
                elif days < 30:
                    score += 1.0
                    reasons.append("active (last commit <30d)")
                else:
                    score -= 1.0
                    reasons.append("stale")
            except Exception:
                pass

        # Completeness
        if readme:
            word_count = len(re.split(r"\s+", readme.strip()))
            if word_count > 200:
                score += 1.5
                reasons.append("rich README")
            elif word_count > 50:
                score += 0.5
                reasons.append("README present")
            else:
                score -= 1.0
                reasons.append("thin README")

        if has_docs:
            score += 1.0
            reasons.append("docs folder")

        if has_tests:
            score += 1.0
            reasons.append("tests present")

        # Issue load
        if open_issues > 50:
            score -= 1.0
            reasons.append("high issue load")
        elif open_issues > 0:
            score += 0.5
            reasons.append("active issues")

        score = max(0.0, min(10.0, score))
        return {
            "name": name,
            "url": url,
            "type": "repo",
            "score": round(score, 1),
            "tags": reasons[:4],
            "raw": {k: v for k, v in repo.items() if k not in ("readme",)},
        }

    def rate_content(self, item: dict, content_type: str = "walkthrough") -> dict:
        """Rate a content item (walkthrough, workflow card, etc.)."""
        name = item.get("title") or item.get("name", "unknown")
        body = item.get("content", "") or item.get("description", "")
        tags = item.get("tags", [])
        score = 5.0
        reasons = []

        word_count = len(re.split(r"\s+", body.strip())) if body else 0
        if word_count > 500:
            score += 2.0
            reasons.append("deep content")
        elif word_count > 100:
            score += 1.0
            reasons.append("solid content")
        else:
            score -= 1.0
            reasons.append("thin content")

        if len(tags) >= 3:
            score += 1.0
            reasons.append("well-tagged")
        elif len(tags) == 0:
            score -= 0.5
            reasons.append("untagged")

        score = max(0.0, min(10.0, score))
        return {
            "name": name,
            "type": content_type,
            "score": round(score, 1),
            "tags": reasons[:4],
        }
