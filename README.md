# Aegis Agent Bridge

Universal email-based sync and orchestration bus for Aegis agents.

## Why Email?

- **Free forever** (Gmail + OneDrive + GitHub free tier)
- **Durable queue** — agents resume from inbox state
- **Human-readable** — every message can be read directly
- **Async by default** — no agents need to be online at the same time

## Components

- `docs/EMAIL_PROTOCOL.md` — strict JSON-over-email protocol for `[TASK]`, `[VOTE]`, `[SYNC]`, etc.
- `docs/AEGIS_DAILY_FORMAT.md` — parser spec for Machine 1's fixed daily email
- `src/inbox_poller.py` — IMAP inbox reader
- `src/parsers/strict.py` — extracts JSON protocol blocks
- `src/parsers/daily.py` — parses Machine 1 daily email
- `src/router.py` — Aegis salience filter + agent routing
- `src/state.py` — agent state KV store
- `tests/` — parser tests

## Quick Start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 src/inbox_poller.py --once
```

## License

Sovereign — use at your own risk.
