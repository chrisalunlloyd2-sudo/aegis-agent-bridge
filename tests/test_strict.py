import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from parsers.strict import parse_email

BODY = """
Hi team,

Please handle this task.

===AEGIS_JSON_START===
{
  "protocol_version": "1.0",
  "message_id": "msg-001",
  "from_agent": "aegis",
  "to_agent": "viper-kernel",
  "action": "task",
  "priority": 2,
  "timestamp": "2026-07-14T15:00:00Z",
  "payload": {"task_id": "t-001", "repo": "chrisalunlloyd2-sudo/wip-quantum-asm"}
}
===AEGIS_JSON_END===

Thanks.
"""

msgs = parse_email("[AGENT:viper-kernel] [TASK] SIMD decode stub", BODY)
assert len(msgs) == 1, f"expected 1 message, got {len(msgs)}"
m = msgs[0]
assert m.agent_to == "viper-kernel"
assert m.action == "task"
assert m.message_id == "msg-001"
assert m.payload["task_id"] == "t-001"
print("test_strict PASS")
