"""Registry of agent adapters available to the router."""
from __future__ import annotations
from jev_router.adapters.claude_code.adapter import ClaudeCodeAdapter
from jev_router.adapters.codex.adapter import CodexAdapter
from jev_router.adapters.opencode.adapter import OpenCodeAdapter
from jev_router.adapters.hermes.adapter import HermesAdapter
from jev_router.adapters.deepagents.adapter import DeepAgentsAdapter
_ADAPTERS = {"claude_code": ClaudeCodeAdapter, "codex": CodexAdapter, "opencode": OpenCodeAdapter,
             "hermes": HermesAdapter, "deepagents": DeepAgentsAdapter}
def get_adapter(name: str): return _ADAPTERS[name]()
def registered() -> list[str]: return sorted(_ADAPTERS)
