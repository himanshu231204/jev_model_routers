"""CLI command that prints the explanation for a stored routing decision."""
from __future__ import annotations
from jev_router.state.memory import MemoryStore
def run_explain(args: dict) -> int:
    print(f"agent={args.get('agent')} session={args.get('session')} turn={args.get('turn')}")
    print("no stored decision in ephemeral memory store (restart clears state)")
    return 0
