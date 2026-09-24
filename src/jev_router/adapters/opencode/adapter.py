from __future__ import annotations
import shutil
from jev_router.contracts.agents import AgentCapabilities
from jev_router.contracts.requests import NormalizedRequest, Message
from jev_router.adapters.opencode.config import provider_entry
class OpenCodeAdapter:
    name = "opencode"
    def detect(self) -> bool: return shutil.which("opencode") is not None
    def capabilities(self) -> AgentCapabilities:
        return AgentCapabilities(supports_custom_provider=True, supports_custom_base_url=True)
    def normalize_request(self, raw: dict):
        text = str(raw.get("prompt", ""))
        return NormalizedRequest(request_id="req_oc", agent="opencode", session_id=raw.get("session_id", ""),
                                 conversation_id=raw.get("session_id", ""), turn_id="t1", prompt=text,
                                 messages=[Message(role="user", content=text)], current_model=raw.get("model"),
                                 available_models=raw.get("available_models", []), tools=[], tool_count=0, metadata={})
    def apply_model(self, raw: dict, model: str) -> dict:
        return {**raw, **provider_entry(model), "model": model}
    def is_new_turn(self, raw: dict) -> bool: return True
    def conversation_key(self, raw: dict) -> str: return str(raw.get("session_id", ""))
