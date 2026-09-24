"""CLI command that lists the configured model catalog and availability."""
from __future__ import annotations
from jev_router.config.loader import load
def run_models(args: dict) -> int:
    cfg = load()
    for m in cfg.get("models", {}).get("allow", []):
        print(m)
    return 0
