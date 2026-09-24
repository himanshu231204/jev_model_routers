from __future__ import annotations
from jev_router.contracts.agents import AgentCapabilities
from jev_router.contracts.requests import NormalizedRequest, Message
class DeepAgentsAdapter:
    name = "deepagents"
    def detect(self) -> bool:
        try: import deepagents; return True
        except ImportError: return False
    def capabilities(self) -> AgentCapabilities:
        return AgentCapabilities(supports_sdk_middleware=True)
    def normalize_request(self, raw: dict):
        text = str(raw.get("prompt", ""))
        return NormalizedRequest(request_id="req_da", agent="deepagents", session_id=raw.get("session_id", ""),
                                 conversation_id=raw.get("session_id", ""), turn_id="t1", prompt=text,
                                 messages=[Message(role="user", content=text)], current_model=raw.get("model"),
                                 available_models=raw.get("available_models", []), tools=[], tool_count=0,
                                 metadata={"subagent_id": raw.get("subagent_id")}, is_subagent=bool(raw.get("subagent_id")))
    def apply_model(self, raw: dict, model: str) -> dict: return {**raw, "model": model}
    def is_new_turn(self, raw: dict) -> bool: return True
    def conversation_key(self, raw: dict) -> str: return str(raw.get("session_id", ""))
