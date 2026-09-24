from __future__ import annotations
from jev_router.contracts.agents import AgentCapabilities
from jev_router.contracts.requests import NormalizedRequest, Message
from jev_router.adapters.hermes.config import split_model
class HermesAdapter:
    name = "hermes"
    def detect(self) -> bool: return False
    def capabilities(self) -> AgentCapabilities:
        return AgentCapabilities(supports_custom_provider=True, supports_custom_base_url=True)
    def normalize_request(self, raw: dict):
        text = str(raw.get("prompt", ""))
        return NormalizedRequest(request_id="req_h", agent="hermes", session_id=raw.get("session_id", ""),
                                 conversation_id=raw.get("session_id", ""), turn_id="t1", prompt=text,
                                 messages=[Message(role="user", content=text)], current_model=raw.get("model"),
                                 available_models=raw.get("available_models", []), tools=[], tool_count=0,
                                 metadata={"tool_result": bool(raw.get("tool_result", False))},
                                 is_new_turn=not bool(raw.get("tool_result", False)))
    def apply_model(self, raw: dict, model: str) -> dict:
        provider, name = split_model(model)
        return {**raw, "provider": provider, "model": name}
    def is_new_turn(self, raw: dict) -> bool: return not bool(raw.get("tool_result", False))
    def conversation_key(self, raw: dict) -> str: return str(raw.get("session_id", ""))
    def launch_command(self, model: str) -> list[str]: return ["hermes", "--model", model]
