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


    def record_vote(self, vote_id: str, voter: str, choice: str, reasoning: str = ""):
        """Record an authorized agent vote. Tally is stored under agent state."""
        if "votes" not in self.data:
            self.data["votes"] = {}
        if vote_id not in self.data["votes"]:
            self.data["votes"][vote_id] = {"tally": {}, "voters": {}, "reasoning": {}}
        tally = self.data["votes"][vote_id]
        if voter in tally["voters"]:
            return {"status": "already_voted", "voter": voter}
        tally["voters"][voter] = choice
        tally["tally"][choice] = tally["tally"].get(choice, 0) + 1
        if reasoning:
            tally["reasoning"][voter] = reasoning
        self.save()
        return {"status": "recorded", "voter": voter, "choice": choice, "tally": tally["tally"]}

    def get_vote_winner(self, vote_id: str) -> tuple:
        tally = self.data.get("votes", {}).get(vote_id, {}).get("tally", {})
        if not tally:
            return None, tally
        winner = max(tally, key=tally.get)
        return winner, tally

    def get_vote_tally(self, vote_id: str) -> dict:
        return self.data.get("votes", {}).get(vote_id, {}).get("voters", {})


    def append_agent_task(self, agent: str, task: dict):
        if "tasks" not in self.data:
            self.data["tasks"] = {}
        if agent not in self.data["tasks"]:
            self.data["tasks"][agent] = []
        self.data["tasks"][agent].append(task)
        self.save()
