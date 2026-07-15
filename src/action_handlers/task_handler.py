"""Emit a [TASK] message to an agent when a vote resolves. ADD only."""
import os
import smtplib
import ssl
from email.message import EmailMessage
from datetime import datetime, timezone


def emit_task(to_agent: str, task_type: str, description: str, parent_vote_id: str = None) -> dict:
    """Send a strict [TASK] email to the target agent. Only add-type tasks."""
    user = os.environ.get("AEGIS_EMAIL")
    password = os.environ.get("AEGIS_PASSWORD")
    if not user or not password:
        raise RuntimeError("AEGIS_EMAIL and AEGIS_PASSWORD must be set")

    subject = f"[AGENT:{to_agent}][TASK:{task_type}] Vote outcome task"
    body = f"""===AEGIS_JSON_START==={{
  "from_agent": "aegis",
  "to_agent": "{to_agent}",
  "action": "TASK",
  "task_type": "{task_type}",
  "description": "{description}",
  "parent_vote_id": "{parent_vote_id or ''}",
  "timestamp": "{datetime.now(timezone.utc).isoformat()}"
}}===AEGIS_JSON_END==="""

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = user
    msg["To"] = user
    msg.set_content(body)

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
        server.login(user, password)
        server.send_message(msg)

    return {"to": to_agent, "task_type": task_type, "sent_at": datetime.now(timezone.utc).isoformat()}
