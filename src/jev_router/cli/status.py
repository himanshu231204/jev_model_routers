"""CLI command that reports current routing status and JEV availability."""
from __future__ import annotations
import os
def run_status(args: dict) -> int:
    if not os.environ.get("JEV_API_KEY"):
        print("routing: disabled (passthrough) — set JEV_API_KEY to enable JEV routing")
        return 0
    print("routing: enabled — JEV key present")
    return 0
