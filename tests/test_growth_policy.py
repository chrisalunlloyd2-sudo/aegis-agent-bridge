"""Test sovereign growth policy: ADD only, 1 repo/day, veto-gated."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from state import AgentState
from action_handlers.growth_policy import GrowthPolicy


def test_add_only_rate_limited():
    s = AgentState("/tmp/test_growth_policy.json")
    s.data = {"agents": {}}
    s.save()
    p = GrowthPolicy(s, daily_repo_limit=1)
    assert p.can_add_repo_today()

    # First repo approved
    s.record_vote("v1", "agent_a", "repo-one", "need repo one")
    s.record_vote("v1", "agent_b", "repo-one", "agreed")
    d = p.evaluate_repo_vote("repo-one", s.get_vote_tally("v1"), ["consensus"])
    assert d.action == "pending"
    a = p.approve_pending("repo-one")
    assert a.action == "add_repo"

    # Second repo blocked by daily limit
    s.record_vote("v2", "agent_a", "repo-two", "need repo two")
    s.record_vote("v2", "agent_b", "repo-two", "agreed")
    d2 = p.evaluate_repo_vote("repo-two", s.get_vote_tally("v2"), ["consensus"])
    assert d2.allowed is False
    assert "limit" in d2.reason.lower()

    # Veto test
    p.record_veto("repo-three", "moe", "duplicate concept")
    s.record_vote("v3", "agent_a", "repo-three", "want repo three")
    d3 = p.evaluate_repo_vote("repo-three", s.get_vote_tally("v3"), ["some reason"])
    assert d3.allowed is False
    assert "veto" in d3.reason.lower()

    print("growth policy tests passed")


if __name__ == "__main__":
    test_add_only_rate_limited()
