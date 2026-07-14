"""Minimal agent state KV store with JSON persistence."""
import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional


class AgentState:
    def __init__(self, path: str = "state.json"):
        self.path = path
        self.data: Dict[str, Any] = self.load()

    def load(self) -> Dict[str, Any]:
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return {}
        return {"agents": {}, "processed_ids": [], "version": 1}

    def save(self):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2)

    def is_processed(self, message_id: str) -> bool:
        return message_id in self.data.get("processed_ids", [])

    def mark_processed(self, message_id: str):
        self.data.setdefault("processed_ids", []).append(message_id)
        self.data["last_processed_at"] = datetime.now(timezone.utc).isoformat()
        self.save()

    def get_agent(self, agent_id: str) -> Dict[str, Any]:
        return self.data.setdefault("agents", {}).setdefault(agent_id, {})

    def set_agent(self, agent_id: str, key: str, value: Any):
        self.get_agent(agent_id)[key] = value
        self.get_agent(agent_id)["updated_at"] = datetime.now(timezone.utc).isoformat()
        self.save()

    def snapshot(self) -> Dict[str, Any]:
        return {"state_path": self.path, "agents": list(self.data.get("agents", {}).keys()), "processed_count": len(self.data.get("processed_ids", []))}
