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


def fetch_unread(cfg: dict) -> List[dict]:
    context = ssl.create_default_context()
    with imaplib.IMAP4_SSL(cfg["imap_host"], cfg["imap_port"], ssl_context=context) as mail:
        mail.login(cfg["email"], cfg["password"])
        mail.select("inbox")
        status, data = mail.search(None, "UNSEEN")
        uids = data[0].split()
        messages = []
        for uid in uids:
            status, msg_data = mail.fetch(uid, "(RFC822)")
            raw = msg_data[0][1]
            msg = email.message_from_bytes(raw)
            subject = msg["Subject"] or ""
            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    ctype = part.get_content_type()
                    if ctype == "text/plain":
                        body = part.get_payload(decode=True).decode("utf-8", errors="ignore")
                        break
            else:
                body = msg.get_payload(decode=True).decode("utf-8", errors="ignore") if msg.get_payload(decode=True) else ""
            messages.append({"uid": uid.decode(), "subject": subject, "body": body, "date": msg["Date"]})
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
    args = parser.parse_args()

    cfg = get_env()
    if not cfg["email"] or not cfg["password"]:
        print("Set AEGIS_EMAIL and AEGIS_PASSWORD environment variables.")
        return 1

    state = AgentState(args.state)
    messages = fetch_unread(cfg)
    print(f"Fetched {len(messages)} unread messages at {datetime.now(timezone.utc).isoformat()}")

    for msg in messages:
        if state.is_processed(msg["uid"]):
            print(f"Skipping already processed UID {msg['uid']}")
            continue
        print(f"Processing: {msg['subject'][:80]}...")
        results = classify_email(msg["subject"], msg["body"])
        for r in results:
            if r["type"] == "strict":
                target = r["agent"] or "aegis"
                print(f"  → route to {target} (salience={r['salience']:.2f}) action={r['message'].action}")
                state.set_agent(target, "last_message", r["message"].message_id)
            elif r["type"] == "daily":
                print(f"  → daily report parsed: {r['report'].projects_count} projects, {r['report'].soak_rounds} soak rounds")
                state.set_agent("aegis", "latest_daily_report", r["report"].__dict__)
        state.mark_processed(msg["uid"])

    print("Snapshot:", state.snapshot())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
