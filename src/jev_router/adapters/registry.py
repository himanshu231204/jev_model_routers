"""Registry of agent adapters available to the router."""
from __future__ import annotations
from jev_router.adapters.claude_code.adapter import ClaudeCodeAdapter
_ADAPTERS = {"claude_code": ClaudeCodeAdapter}
def get_adapter(name: str):
    return _ADAPTERS[name]()
def registered() -> list[str]:
    return sorted(_ADAPTERS)
