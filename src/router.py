import json
"""Aegis salience router: decides which agent handles a message."""
from typing import List, Optional
from parsers.strict import ParsedMessage


AGENT_ROUTING = {
    "viper-kernel": ["kernel", "gpu", "gguf", "quantization", "simd"],
    "quantum-asm": ["quantum", "asm", "ast", "bytecode"],
    "moe-gate": ["moe", "gate", "mixture", "certify"],
    "hero-house": ["hero", "training", "soak", "foundry"],
    "kai9000ce": ["apk", "android", "termux", "build"],
    "foundry-ui": ["ui", "dashboard", "ascii", "web"],
    "gitauto": ["commit", "push", "repo", "merge", "pr"],
}


def route(message: ParsedMessage) -> Optional[str]:
    """Return target agent ID or None if human/aegis should handle."""
    if message.agent_to and message.agent_to != "broadcast":
        return message.agent_to

    payload_text = json.dumps(message.payload).lower()
    subject_text = " ".join(message.subject_tags).lower()
    combined = f"{subject_text} {payload_text}"

    scores = {}
    for agent, keywords in AGENT_ROUTING.items():
        scores[agent] = sum(1 for kw in keywords if kw in combined)

    if scores:
        best = max(scores, key=scores.get)
        if scores[best] > 0:
            return best
    return None


def salience(message: ParsedMessage, alert_count_30d: int = 0, user_priority: float = 1.0) -> float:
    """Compute salience score. Higher = more urgent."""
    tau = (alert_count_30d * 0.5) + (user_priority * 1.2)
    priority = message.priority
    if "ROLLBACK" in message.subject_tags or "BLOCKED" in message.subject_tags:
        priority += 5
    if message.action in ("rollback", "blocked", "debug"):
        priority += 2
    return priority + tau
