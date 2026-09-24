"""Classification of normalized requests: fresh user turn versus tool-loop continuation, auxiliary, or manual."""
from __future__ import annotations
import enum
from jev_router.contracts.requests import NormalizedRequest

class RequestKind(str, enum.Enum):
    FRESH_TURN = "fresh_turn"
    TOOL_CONTINUATION = "tool_continuation"
    AUXILIARY = "auxiliary"
    SUBAGENT = "subagent"

_AUX_KEYS = {"summary", "title", "metadata", "compression", "health", "models_list"}

def classify(request: NormalizedRequest) -> RequestKind:
    meta = request.metadata or {}
    kind = str(meta.get("kind", "")).lower()
    if kind in _AUX_KEYS or meta.get("auxiliary") is True:
        return RequestKind.AUXILIARY
    if request.is_subagent:
        return RequestKind.SUBAGENT
    if meta.get("tool_result") is True or request.is_new_turn is False:
        if request.is_new_turn is True and not meta.get("tool_result"):
            return RequestKind.FRESH_TURN
        return RequestKind.TOOL_CONTINUATION
    return RequestKind.FRESH_TURN
