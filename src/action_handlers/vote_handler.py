"""Handle internal agent [VOTE] messages. Only authorized agents may vote."""
from dataclasses import dataclass
from typing import Optional
from .growth_policy import GrowthPolicy


@dataclass
class VoteResult:
    authorized: bool
    voter: Optional[str]
    choice: Optional[str]
    vote_id: Optional[str]
    error: Optional[str] = None


def handle_vote(message, state) -> VoteResult:
    """
    Process a strict [VOTE] message.
    Authorized voters are agents known to the bridge state plus 'moe' and the user.
    Public/anonymous votes are rejected.
    """
    params = getattr(message, "params", {})
    if not isinstance(params, dict):
        params = {}

    voter = getattr(message, "agent_from", None) or params.get("from_agent")
    choice = params.get("choice")
    vote_id = params.get("vote_id")
    reasoning = params.get("reasoning", "")

    if not voter:
        return VoteResult(False, None, choice, vote_id, "Missing from_agent / voter")

    # Authorized agent list from state; user and moe are always authorized.
    authorized = set(state.data.get("agents", {}).keys())
    authorized.update({"moe", "chris", "chrisalunlloyd2", "user"})

    if voter not in authorized:
        return VoteResult(False, voter, choice, vote_id, f"Unauthorized voter: {voter}")

    # Check for user/Moe explicit veto on this vote_id or choice
    vetos = state.data.get("growth", {}).get("vetos", [])
    for v in vetos:
        if v.get("repo") == choice or v.get("vote_id") == vote_id:
            return VoteResult(False, voter, choice, vote_id, f"Veto active by {v.get('by')}")

    result = state.record_vote(vote_id or "default", voter, choice, reasoning=reasoning)
    if result.get("status") == "already_voted":
        return VoteResult(True, voter, choice, vote_id, "Already voted; ignored")

    # Evaluate if this vote triggers a growth decision
    tally = state.get_vote_tally(vote_id or "default")
    if not tally:
        return VoteResult(True, voter, choice, vote_id, "no tally yet")
    # Determine winning repo from tally
    from collections import Counter
    winner = Counter(tally.values()).most_common(1)[0][0]
    policy = GrowthPolicy(state)
    decision = policy.evaluate_repo_vote(winner, tally, sources=[reasoning or f"vote by {voter}"])
    if decision.allowed and decision.action == "pending":
        pending = policy.pending_decisions()
        execute_after = pending[-1].get("execute_after") if pending else ""
        state.set_agent("aegis", "pending_repo_decision", {
            "repo": decision.repo_name,
            "votes": tally,
            "execute_after": execute_after
        })

    return VoteResult(True, voter, choice, vote_id, f"growth_decision={decision.action}")
