"""CLI command that lists detected coding agents and their adapter status."""
from __future__ import annotations
from jev_router.adapters.registry import registered, get_adapter
def run_agents(args: dict) -> int:
    for name in registered():
        try: ok = get_adapter(name).detect()
        except Exception: ok = False
        print(f"{name}: {'detected' if ok else 'not detected'}")
    return 0
