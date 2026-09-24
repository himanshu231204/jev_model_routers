"""Turn lifecycle state: records routing decisions and pins the selected model through the tool loop."""
from __future__ import annotations
import time
from dataclasses import dataclass

@dataclass
class TurnState:
    turn_id: str
    model: str
    tier: str = "balanced"
    created_at: float = 0.0
    reason: str = ""
    confidence: float | None = None

    def __post_init__(self):
        if not self.created_at:
            self.created_at = time.time()

def state_key(agent: str, session_id: str, conversation_id: str, subagent_id: str | None) -> str:
    base = f"{agent}:{session_id}:{conversation_id}"
    return f"{base}:{subagent_id}" if subagent_id else base
