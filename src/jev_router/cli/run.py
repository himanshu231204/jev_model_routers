"""CLI command that launches or attaches to a coding agent with JEV routing enabled."""
from __future__ import annotations
from jev_router.adapters.registry import get_adapter
def run_run(args: dict) -> int:
    name = args.get("agent", "claude_code")
    print(f"starting router for agent: {name} (adapter={get_adapter(name).name})")
    return 0
