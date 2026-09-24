"""Explicit human model-override detection and precedence over automatic routing."""
from __future__ import annotations
import re
from dataclasses import dataclass
from typing import Literal

@dataclass
class UserOverride:
    kind: Literal["exact_model", "tier", "disable_router"]
    value: str

_TIER_WORDS = {"fast": "fast", "balanced": "balanced", "strong": "strong", "opus": "strong", "sonnet": "balanced", "haiku": "fast"}
_PAT = re.compile(r"\buse\s+([a-z0-9\-_/\.]+)", re.IGNORECASE)

def detect_override(prompt: str, native_model: str | None) -> UserOverride | None:
    if native_model:
        return UserOverride(kind="exact_model", value=native_model)
    if not prompt:
        return None
    low = prompt.lower().strip()
    if low in ("no router", "disable router", "passthrough"):
        return UserOverride(kind="disable_router", value="passthrough")
    m = _PAT.search(prompt)
    if not m:
        return None
    token = m.group(1).lower()
    if token in _TIER_WORDS:
        return UserOverride(kind="tier", value=_TIER_WORDS[token])
    if "/" in token or token.startswith("claude") or token.startswith("gpt") or token.startswith("openai"):
        return UserOverride(kind="exact_model", value=m.group(1))
    return None
