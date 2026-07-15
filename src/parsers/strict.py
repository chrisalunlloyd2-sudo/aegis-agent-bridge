"""Parse strict Aegis JSON-over-email protocol blocks."""
import json
import re
from dataclasses import dataclass, field
from typing import List, Optional

JSON_START = "===AEGIS_JSON_START==="
JSON_END = "===AEGIS_JSON_END==="


@dataclass
class ParsedMessage:
    subject_tags: List[str]
    agent_to: Optional[str]
    agent_from: Optional[str]
    action: str
    priority: int
    message_id: str
    thread_id: Optional[str]
    timestamp: str
    expires_at: Optional[str]
    payload: dict
    raw_json: dict
    raw_body: str = ""
    params: dict = field(default_factory=dict)


def extract_subject_tags(subject: str) -> tuple[List[str], Optional[str]]:
    """Extract bracketed tags and agent target from subject."""
    tags = re.findall(r"\[([^\]]+)\]", subject)
    agent_to = None
    cleaned_tags = []
    for tag in tags:
        if tag.lower().startswith("agent:"):
            agent_to = tag.split(":", 1)[1].strip()
        else:
            cleaned_tags.append(tag.strip())
    return cleaned_tags, agent_to


def extract_json_blocks(body: str) -> List[dict]:
    """Extract all JSON blocks wrapped in protocol markers."""
    pattern = re.compile(
        re.escape(JSON_START) + r"\s*(.*?)\s*" + re.escape(JSON_END),
        re.DOTALL,
    )
    results = []
    for match in pattern.finditer(body):
        text = match.group(1).strip()
        try:
            results.append(json.loads(text))
        except json.JSONDecodeError as e:
            # Try stripping common quoted-printable noise
            clean = text.replace("=\n", "").replace("=3D", "=")
            try:
                results.append(json.loads(clean))
            except json.JSONDecodeError:
                raise ValueError(f"Invalid JSON block: {e}")
    return results


def parse_email(subject: str, body: str, raw_body: str = None) -> List[ParsedMessage]:
    """Parse one email into zero or more protocol messages."""
    subject_tags, subject_agent = extract_subject_tags(subject)
    blocks = extract_json_blocks(body)
    messages = []
    for block in blocks:
        agent_to = block.get("to_agent") or subject_agent
        params = block.get("params", {})
        if not isinstance(params, dict):
            params = {}
        messages.append(
            ParsedMessage(
                subject_tags=subject_tags,
                agent_to=agent_to,
                agent_from=block.get("from_agent"),
                action=block.get("action", "unknown"),
                priority=int(block.get("priority", 1)),
                message_id=block.get("message_id", ""),
                thread_id=block.get("thread_id"),
                timestamp=block.get("timestamp", ""),
                expires_at=block.get("expires_at"),
                payload=block.get("payload", {}),
                raw_json=block,
                raw_body=raw_body or body,
                params=params,
            )
        )
    return messages
