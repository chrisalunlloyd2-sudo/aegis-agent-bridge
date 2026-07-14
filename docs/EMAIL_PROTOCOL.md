# Aegis Agent Email Sync Protocol v1.0

## Purpose
Use email (free, durable, always available) as the universal message bus for agent orchestration across GitHub repos, cloud APIs, OneDrive, and local devices.

## Philosophy
- **Async by default**: Agents do not need to be online simultaneously.
- **Durable pipeline**: Email queues naturally. Lost agents resume from inbox state.
- **Free forever**: Gmail + OneDrive + GitHub free tier.
- **Human-readable**: Any email can be read by a human in a pinch.

---

## Subject Tags

Subjects use bracketed action tags. Multiple tags allowed, comma-separated.

| Tag | Meaning |
|---|---|
| `[AGENT]` | Directed at a specific agent |
| `[BROADCAST]` | Sent to all agents |
| `[TASK]` | New assignment / TODO |
| `[VOTE]` | Request for ranked decision |
| `[SYNC]` | State snapshot / heartbeat |
| `[ROLLBACK]` | Revert to checkpoint |
| `[MERGE]` | Combine partial outputs |
| `[AST]` | Abstract syntax tree / code tree update |
| `[DEBUG]` | Error trace, needs triage |
| `[DONE]` | Task complete, report attached |
| `[BLOCKED]` | Agent needs human / other agent input |

### Examples
```
[AGENT:viper-kernel] [TASK] implement Q4_K SIMD decode stub
[BROADCAST] [SYNC] nightly agent state dump
[AGENT:aegis] [VOTE] which repo should get next build cycle?
[AGENT:foundry-ui] [ROLLBACK] rollback_point.2026-07-14T03:00:00Z
```

---

## Body Schema

Every protocol email body contains a JSON block wrapped in markers. Preceding/following human text is allowed.

```
===AEGIS_JSON_START===
{
  "protocol_version": "1.0",
  "message_id": "uuid-or-increment",
  "thread_id": "parent-message-id-or-null",
  "from_agent": "agent-id",
  "to_agent": "agent-id-or-broadcast",
  "action": "task|vote|sync|rollback|merge|debug|done|blocked",
  "priority": 1,
  "timestamp": "2026-07-14T15:00:00Z",
  "expires_at": "2026-07-15T15:00:00Z",
  "payload": {}
}
===AEGIS_JSON_END===
```

---

## Action Payloads

### `task`
```json
{
  "action": "task",
  "payload": {
    "task_id": "t-001",
    "repo": "chrisalunlloyd2-sudo/wip-quantum-asm",
    "branch": "main",
    "title": "Implement Q4_K block decoder",
    "description": "Create q4_k_decode function in src/kernels/...",
    "acceptance_criteria": ["passes unit tests", "no regressions"],
    "artifacts": [
      {"type": "github_issue", "url": "..."},
      {"type": "onedrive_doc", "url": "..."}
    ],
    "rollback_point": "rollback_point.2026-07-14T15:00:00Z"
  }
}
```

### `vote`
```json
{
  "action": "vote",
  "payload": {
    "vote_id": "v-001",
    "question": "Next repo to receive build cycle?",
    "options": ["wip-quantum-asm", "MatrixCE_GUI", "kai9000ce-apk"],
    "deadline": "2026-07-14T18:00:00Z",
    "method": "ranked_choice"
  }
}
```

### `sync`
```json
{
  "action": "sync",
  "payload": {
    "agent_state": {
      "agent_id": "viper-kernel",
      "status": "idle",
      "current_task": null,
      "memory_keys": ["self_email.80355", "global_keywords"],
      "kv_checksum": "sha256:..."
    },
    "deliverables": []
  }
}
```

### `rollback`
```json
{
  "action": "rollback",
  "payload": {
    "checkpoint_id": "rollback_point.2026-07-14T15:00:00Z",
    "scope": ["repo", "kv", "kg"],
    "reason": "build regression in MatrixCE_GUI"
  }
}
```

### `done`
```json
{
  "action": "done",
  "payload": {
    "task_id": "t-001",
    "repo": "chrisalunlloyd2-sudo/wip-quantum-asm",
    "commit_sha": "abc1234",
    "summary": "Q4_K decoder implemented and tested",
    "artifacts": [
      {"type": "commit", "url": "https://github.com/.../abc1234"},
      {"type": "test_report", "url": "..."}
    ]
  }
}
```

### `blocked`
```json
{
  "action": "blocked",
  "payload": {
    "task_id": "t-001",
    "reason": "missing spec for Q5_K layout",
    "needs_from": "aegis-or-human",
    "proposed_resolution": "generate Q5_K spec from llama.cpp docs"
  }
}
```

---

## Agent IDs (canonical)

| Agent ID | Role |
|---|---|
| `aegis` | Orchestrator / salience filter |
| `foundry-ui` | Web dashboards, ASCII art, interfaces |
| `viper-kernel` | GPU kernels, GGUF, quantization |
| `quantum-asm` | Deterministic quantum assembly bots |
| `moe-gate` | Mixture-of-Experts wrapper / gating |
| `hero-house` | Kernel training system |
| `kai9000ce` | Android / Termux APK build agent |
| `gitauto` | Repo automation, commits, pushes |
| `bridge-human` | You (human in the loop) |

---

## Processing Rules

1. **Order by timestamp**, not inbox order.
2. **Ignore expired messages** unless explicitly revived.
3. **ACK required**: agents reply `[DONE]` or `[BLOCKED]` to `[TASK]` within deadline.
4. **Idempotency**: same `message_id` processed once, logged forever.
5. **Conflict resolution**: Aegis breaks ties using salience score.
6. **Rollback always wins**: a `[ROLLBACK]` for a scope pauses all tasks in that scope.

---

## OneDrive Integration

- Large artifacts attach as OneDrive share links.
- Subject tag `[DRIVE]` indicates body contains OneDrive references.
- Email body always carries at least the JSON metadata block; the actual AST/code tree lives in OneDrive.

---

## GitHub Integration

- Each `[TASK]` with a repo field creates a GitHub issue if one does not exist.
- `[DONE]` emails close the issue and reference the commit.
- `[MERGE]` emails trigger PR creation via `Gitautoworks` agent.

---

## Next Steps

1. Implement inbox poller in Python that extracts `===AEGIS_JSON_START===` blocks.
2. Add Aegis routing logic: salience filter + assignment.
3. Add `living-ascii-art` voting endpoint that emits `[VOTE]` emails.
4. Create `aegis-agent-bridge` repo to host the protocol implementation.
