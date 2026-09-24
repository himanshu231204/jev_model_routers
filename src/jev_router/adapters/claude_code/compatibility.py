"""Claude Code protocol-version compatibility handling, isolated from the routing core."""
from __future__ import annotations
_SUPPORTED = {"2026-09", "2026-06"}
def normalize_version(v: str | None) -> str:
    return v if v in _SUPPORTED else "2026-09"
