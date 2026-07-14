#!/usr/bin/env python3
"""IMAP inbox poller for Aegis Agent Bridge."""
import argparse
import email
import imaplib
import os
import ssl
from datetime import datetime, timezone
from typing import List

from parsers.strict import parse_email
from parsers.daily import parse_daily_email
from router import route, salience
from state import AgentState


def get_env():
    return {
        "imap_host": os.getenv("AEGIS_IMAP_HOST", "imap.gmail.com"),
        "imap_port": int(os.getenv("AEGIS_IMAP_PORT", "993")),
        "email": os.getenv("AEGIS_EMAIL"),
        "password": os.getenv("AEGIS_PASSWORD"),
    }


def _build_subject_query(subjects: list) -> str:
    """Build nested IMAP OR query for multiple subjects."""
    if len(subjects) == 1:
        return f'SUBJECT "{subjects[0]}"'
    query = f'SUBJECT "{subjects[-1]}"'
    for subj in reversed(subjects[:-1]):
        query = f'(OR SUBJECT "{subj}" {query})'
    return query


def _build_search_query(since_days: int, subjects: list) -> str:
    from datetime import datetime, timedelta, timezone
    since = (datetime.now(timezone.utc) - timedelta(days=since_days)).strftime("%d-%b-%Y")
    return f'(SINCE {since} {_build_subject_query(subjects)})'


def fetch_recent(cfg: dict, since_days: int = 3, limit: int = 50, peek: bool = True) -> List[dict]:
    context = ssl.create_default_context()
    with imaplib.IMAP4_SSL(cfg["imap_host"], cfg["imap_port"], ssl_context=context, timeout=15) as mail:
        mail.login(cfg["email"], cfg["password"])
        mail.select("inbox")
        subjects = ["Aegis", "Nightly Dream", "kai collective"]
        query = _build_search_query(since_days, subjects)
        print(f"IMAP query: {query}")
        status, data = mail.search(None, query)
        uids = data[0].split()[-limit:]
        messages = []
        fetch_spec = "(BODY.PEEK[])" if peek else "(RFC822)"
        for uid in uids:
            try:
                status, msg_data = mail.fetch(uid, fetch_spec)
                raw = msg_data[0][1]
                msg = email.message_from_bytes(raw)
                subject = str(msg.get("Subject", ""))
                body = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        ctype = part.get_content_type()
                        if ctype == "text/plain":
                            payload = part.get_payload(decode=True)
                            body = payload.decode("utf-8", errors="ignore") if payload else ""
                            break
                else:
                    payload = msg.get_payload(decode=True)
                    body = payload.decode("utf-8", errors="ignore") if payload else ""
                messages.append({"uid": uid.decode(), "subject": subject, "body": body, "date": msg["Date"]})
            except Exception as e:
                print(f"WARN: failed to fetch UID {uid.decode()}: {e}")
        return messages

def classify_email(subject: str, body: str) -> List[dict]:
    results = []
    # Strict protocol messages
    strict_messages = parse_email(subject, body)
    for m in strict_messages:
        results.append({"type": "strict", "agent": route(m), "salience": salience(m), "message": m})
    # Daily report (heuristic: contains signature header)
    if "Morning Chris — Aegis here with your daily foundry read" in body or "Viper Soak — Daily Check-in" in body:
        report = parse_daily_email(body)
        results.append({"type": "daily", "report": report})
    return results


def main():
    parser = argparse.ArgumentParser(description="Aegis Agent Bridge Inbox Poller")
    parser.add_argument("--once", action="store_true", help="Run one poll and exit")
    parser.add_argument("--state", default="state.json", help="State file path")
    parser.add_argument("--dry-run", action="store_true", help="Do not write state; just log what would be processed")
    args = parser.parse_args()

    cfg = get_env()
    if not cfg["email"] or not cfg["password"]:
        print("Set AEGIS_EMAIL and AEGIS_PASSWORD environment variables.")
        return 1

    state = AgentState(args.state) if not args.dry_run else None
    messages = fetch_recent(cfg)
    print(f"Fetched {len(messages)} recent messages at {datetime.now(timezone.utc).isoformat()}")

    for msg in messages:
        if state and state.is_processed(msg["uid"]):
            print(f"Skipping already processed UID {msg['uid']}")
            continue
        print(f"Processing: {msg['subject'][:80]}...")
        results = classify_email(msg["subject"], msg["body"])
        for r in results:
            if r["type"] == "strict":
                target = r["agent"] or "aegis"
                print(f"  → route to {target} (salience={r['salience']:.2f}) action={r['message'].action}")
                if state:
                    state.set_agent(target, "last_message", r["message"].message_id)
            elif r["type"] == "daily":
                print(f"  → daily report parsed: {r['report'].projects_count} projects, {r['report'].soak_rounds} soak rounds")
                if state:
                    state.set_agent("aegis", "latest_daily_report", r["report"].__dict__)
        if state:
            state.mark_processed(msg["uid"])

    if state:
        print("Snapshot:", state.snapshot())
    else:
        print("Dry run complete — no state written")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
