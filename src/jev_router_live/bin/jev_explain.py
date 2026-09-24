#!/usr/bin/env python3
"""Port of jev-router's ``bin/jev-explain.mjs``."""
from __future__ import annotations

import os
import sys

from jev_router_live.explain import format_explanation
from jev_router_live.status import read_status


def main() -> None:
    session_id = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("JEV_CODEX_STATUS_ID")
    sys.stdout.write(f"{format_explanation(read_status(session_id))}\n")


if __name__ == "__main__":
    main()
