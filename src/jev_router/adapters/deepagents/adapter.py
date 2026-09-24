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
                                 metadata={"subagent_id": raw.get("subagent_id"), "tool_result": bool(raw.get("tool_result", False))},
                                 is_subagent=bool(raw.get("subagent_id")),
                                 is_new_turn=not bool(raw.get("tool_result", False)))
    def apply_model(self, raw: dict, model: str) -> dict: return {**raw, "model": model}
    def is_new_turn(self, raw: dict) -> bool: return not bool(raw.get("tool_result", False))
    def conversation_key(self, raw: dict) -> str: return str(raw.get("session_id", ""))
    def launch_command(self, model: str) -> list[str]:
        raise NotImplementedError(
            "deepagents has no standalone CLI binary; it's embedded via "
            "adapters/deepagents/adapter.py and middleware.py, not launched as a subprocess."
        )
