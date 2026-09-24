"""Claude Code adapter: detects fresh turns, normalizes requests, and applies resolved models."""
from __future__ import annotations
import shutil
from jev_router.contracts.agents import AgentCapabilities
from jev_router.adapters.claude_code.parser import parse
from jev_router.adapters.claude_code.compatibility import normalize_version

# Maps this router's internal catalog ids (configs/default.yaml `models.allow`) to aliases
# `claude --model` actually accepts, verified against `claude --help`. Ids not in this table
# are passed through unchanged -- if they're not a real Claude Code model/alias, the launch
# will fail with Claude Code's own error, same as before this table existed.
_MODEL_ALIASES = {
    "anthropic/claude-sonnet": "sonnet",
    "anthropic/claude-opus": "opus",
}

class ClaudeCodeAdapter:
    name = "claude_code"
    def detect(self) -> bool:
        return shutil.which("claude") is not None
    def capabilities(self) -> AgentCapabilities:
        return AgentCapabilities(supports_proxy=True, supports_custom_base_url=True, supports_streaming_intercept=True, supports_subagent_identification=True)
    def normalize_request(self, raw: dict):
        n = parse(raw); n.agent_version = normalize_version(raw.get("agent_version")); return n
    def apply_model(self, raw: dict, model: str) -> dict:
        return {**raw, "model": model}
    def is_new_turn(self, raw: dict) -> bool:
        return not bool(raw.get("tool_result")) and "tool_calls" not in str(raw.get("messages", ""))
    def conversation_key(self, raw: dict) -> str:
        return str(raw.get("session_id", ""))
    def launch_command(self, model: str) -> list[str]:
        return ["claude", "--model", _MODEL_ALIASES.get(model, model)]
