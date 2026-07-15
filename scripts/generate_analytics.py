"""
Generate analytics.json for the Aegis Sovereign Analytics dashboard.
Correlates bridge state (votes, pending decisions) with traffic data to produce
a daily hypothesis and keyword rankings.
"""
import json
import os
import re
from datetime import datetime, timezone
from collections import Counter, defaultdict

from src.analytics.metadata_rater import MetadataRater
from src.analytics.keyword_index import KeywordIndex
from src.analytics.hypothesis_tracker import HypothesisTracker


def load_json(path: str, default=None) -> dict:
    if not os.path.exists(path):
        return default if default is not None else {}
    with open(path) as f:
        return json.load(f)


def extract_keywords(text: str) -> list:
    stop = {"the", "and", "for", "with", "from", "this", "that", "need", "needs", "clean", "new", "a", "an", "is", "it"}
    words = re.findall(r"[a-zA-Z][a-zA-Z0-9_-]{3,}", text.lower())
    counts = Counter(w for w in words if w not in stop)
    return [w for w, _ in counts.most_common(8)]


def generate_hypothesis(state: dict, traffic: dict, data: dict) -> dict:
    pending = state.get("growth", {}).get("pending", [])
    if not pending:
        return None
    top = pending[0]
    repo = top.get("repo", "unknown")
    votes = top.get("votes", {})
    sources = top.get("sources", [])
    keywords = [repo] + [v for v in votes.keys() if v != repo] + extract_keywords(" ".join(sources))
    keywords = list(dict.fromkeys(keywords))[:6]

    return {
        "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "title": f"Develop content around '{repo}'",
        "description": (
            f"Internal agent vote converged on {repo} ({len(votes)} agents). "
            "Hypothesis: publishing a walkthrough targeting associated keywords will increase relevant traffic."
        ),
        "keywords": keywords,
        "metric": "page_views",
        "baseline_value": float(traffic.get("page_views", 0)),
        "status": "running",
    }


def build_keyword_index(data: dict, state: dict) -> KeywordIndex:
    idx = KeywordIndex()
    for repo in data.get("repos", []):
        idx.add_repo(repo)
    for wt in data.get("walkthroughs", []):
        idx.add_walkthrough(wt)
    for card in data.get("workflow_cards", []):
        idx.add_card(card)
    # Add reasoning from bridge votes
    for vote_id, vote_data in state.get("votes", {}).items():
        for reason in (vote_data.get("reasoning") or {}).values():
            idx.add_document(f"vote:{vote_id}", reason, "agent_reasoning", 1.5)
        for choice, count in (vote_data.get("tally") or {}).items():
            idx.add_document(f"vote:{vote_id}", f"{choice} " * count, "vote_choice", 2.0)
    return idx


def rate_metadata(data: dict) -> list:
    rater = MetadataRater()
    ratings = []
    for repo in data.get("repos", []):
        ratings.append(rater.rate_repo(repo))
    for wt in data.get("walkthroughs", []):
        ratings.append(rater.rate_content(wt, "walkthrough"))
    for card in data.get("workflow_cards", []):
        ratings.append(rater.rate_content(card, "workflow_card"))
    return sorted(ratings, key=lambda x: x["score"], reverse=True)


def main():
    base = os.path.dirname(os.path.dirname(__file__))
    state_path = os.path.join(base, "state.json")
    bridge_state_path = os.path.join(base, "bridge_state.json")
    traffic_path = os.path.join(base, "traffic.json")
    data_path = os.path.join(base, "..", "living-ascii-art", "data.json")
    out_dir = os.path.join(base, "..", "living-ascii-art", "analytics")
    out_path = os.path.join(out_dir, "analytics.json")

    state = load_json(state_path) if os.path.exists(state_path) else load_json(bridge_state_path, {})
    traffic = load_json(traffic_path, {"page_views": 0, "history": []})
    data = load_json(data_path, {})
    prev = load_json(out_path, {})

    # Archive previous hypothesis
    tracker = HypothesisTracker(prev)
    hypotheses = tracker.archive_yesterday(traffic)

    # Generate today's hypothesis from top pending vote
    new_hypothesis = generate_hypothesis(state, traffic, data)
    if new_hypothesis:
        if not hypotheses or hypotheses[0].get("title") != new_hypothesis["title"]:
            hypotheses.insert(0, new_hypothesis)

    # Build keyword index
    idx = build_keyword_index(data, state)
    rankings = idx.rankings(top_n=30)
    reverse_search_enabled = True

    # Rate metadata
    ratings = rate_metadata(data)

    analytics = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "hypotheses": hypotheses[:30],
        "keyword_rankings": rankings,
        "metadata_ratings": ratings,
        "reverse_search_index": reverse_search_enabled,
    }

    os.makedirs(out_dir, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(analytics, f, indent=2)
    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
