"""Sovereign growth policy: ADD only, rate-limited, veto-gated."""
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional


@dataclass
class GrowthDecision:
    allowed: bool
    reason: str
    action: Optional[str] = None  # "add_repo", "none", "blocked"
    repo_name: Optional[str] = None


class GrowthPolicy:
    """
    Core rules:
    1. ADD only — never delete repos, files, or keys unless explicitly approved.
    2. Rate limit: max 1 repo addition per day across all agents.
    3. Auto-execute only when no user/Moe veto exists and consensus is clear.
    4. Veto window: decisions sit for a configurable cooldown (default 1 hour) before execution,
       giving user and Moe time to review.
    """

    def __init__(self, state, daily_repo_limit: int = 1, veto_hours: float = 1.0):
        self.state = state
        self.daily_repo_limit = daily_repo_limit
        self.veto_hours = veto_hours

    def todays_added_repos(self) -> list:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        adds = self.state.data.get("growth", {}).get("repo_adds", [])
        return [a for a in adds if a.get("date", "").startswith(today)]

    def can_add_repo_today(self) -> bool:
        return len(self.todays_added_repos()) < self.daily_repo_limit

    def record_repo_add(self, repo_name: str, source: str):
        if "growth" not in self.state.data:
            self.state.data["growth"] = {"repo_adds": [], "vetos": []}
        self.state.data["growth"]["repo_adds"].append({
            "date": datetime.now(timezone.utc).isoformat(),
            "repo": repo_name,
            "source": source,
        })
        self.state.save()

    def record_veto(self, repo_name: str, veto_by: str, reason: str):
        if "growth" not in self.state.data:
            self.state.data["growth"] = {"repo_adds": [], "vetos": []}
        self.state.data["growth"]["vetos"].append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "repo": repo_name,
            "by": veto_by,
            "reason": reason,
        })
        self.state.save()

    def is_vetoed(self, repo_name: str) -> bool:
        vetos = self.state.data.get("growth", {}).get("vetos", [])
        return any(v.get("repo") == repo_name for v in vetos)

    def pending_decisions(self) -> list:
        return self.state.data.get("growth", {}).get("pending", [])

    def add_pending_decision(self, decision: dict):
        if "growth" not in self.state.data:
            self.state.data["growth"] = {"repo_adds": [], "vetos": [], "pending": []}
        self.state.data["growth"].setdefault("pending", []).append(decision)
        self.state.save()

    def approve_pending(self, repo_name: str) -> GrowthDecision:
        pending = self.pending_decisions()
        for d in pending:
            if d.get("repo") == repo_name:
                if self.is_vetoed(repo_name):
                    return GrowthDecision(False, f"Repo {repo_name} is vetoed", "blocked", repo_name)
                if not self.can_add_repo_today():
                    return GrowthDecision(False, "Daily repo limit reached", "none", repo_name)
                self.record_repo_add(repo_name, d.get("source", "vote"))
                # remove from pending
                self.state.data["growth"]["pending"] = [p for p in pending if p.get("repo") != repo_name]
                self.state.save()
                return GrowthDecision(True, "Approved and recorded", "add_repo", repo_name)
        return GrowthDecision(False, f"No pending decision for {repo_name}", "none", repo_name)

    def evaluate_repo_vote(self, repo_name: str, votes: dict, sources: list) -> GrowthDecision:
        """
        Decide whether a proposed repo can move to pending/approval.
        votes: {agent_id: choice}
        sources: list of supporting evidence strings
        """
        if self.is_vetoed(repo_name):
            return GrowthDecision(False, f"Vetoed: {repo_name}", "blocked", repo_name)

        total = len(votes)
        if total == 0:
            return GrowthDecision(False, "No votes", "none", repo_name)

        for_repo = sum(1 for v in votes.values() if v == repo_name)
        consensus = for_repo / total

        if consensus < 0.51:
            return GrowthDecision(False, f"Consensus {consensus:.0%} < 51%", "none", repo_name)

        if not self.can_add_repo_today():
            return GrowthDecision(False, "Daily repo limit reached", "none", repo_name)

        # Place in pending for veto window
        self.add_pending_decision({
            "repo": repo_name,
            "votes": votes,
            "sources": sources,
            "proposed_at": datetime.now(timezone.utc).isoformat(),
            "execute_after": (datetime.now(timezone.utc).replace(second=0, microsecond=0)
                              .isoformat()),  # will be adjusted by veto_hours caller
        })
        return GrowthDecision(True, f"Pending approval: {repo_name} ({for_repo}/{total} votes)", "pending", repo_name)
