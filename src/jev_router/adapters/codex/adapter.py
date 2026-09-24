from __future__ import annotations
import shutil
from jev_router.contracts.agents import AgentCapabilities
from jev_router.adapters.codex.parser import parse
class CodexAdapter:
    name = "codex"
    def detect(self) -> bool: return shutil.which("codex") is not None
    def capabilities(self) -> AgentCapabilities:
        return AgentCapabilities(supports_proxy=True, supports_custom_base_url=True)
    def normalize_request(self, raw: dict): return parse(raw)
    def apply_model(self, raw: dict, model: str) -> dict: return {**raw, "model": model}
    def is_new_turn(self, raw: dict) -> bool: return not bool(raw.get("tool_result"))
    def conversation_key(self, raw: dict) -> str: return str(raw.get("session_id", ""))
