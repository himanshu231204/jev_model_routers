"""Policy engine that evaluates JEV decisions against overrides, confidence, and compatibility rules."""
from __future__ import annotations
from typing import Any
from jev_router.contracts.requests import NormalizedRequest
from jev_router.core.decision import PolicyDecision
from jev_router.core.overrides import UserOverride

_DEFAULT_THRESHOLDS = {"low": 0.30, "medium": 0.60, "high": 0.85}

class Policy:
    def __init__(self, thresholds: dict[str, float] | None = None):
        self.thresholds = {**_DEFAULT_THRESHOLDS, **(thresholds or {})}

    def evaluate(self, request: NormalizedRequest, jev: dict[str, Any] | None,
                 override: UserOverride | None) -> PolicyDecision:
        if override is not None:
            if override.kind == "disable_router":
                return PolicyDecision(allowed=True, tier=None, requested_model=request.current_model,
                                      reason="router_disabled", fallback=False, confidence=1.0)
            if override.kind == "exact_model":
                return PolicyDecision(allowed=True, tier=None, requested_model=override.value,
                                      reason="explicit_override", fallback=False, confidence=1.0)
            return PolicyDecision(allowed=True, tier=override.value, requested_model=None,
                                  reason="explicit_override", fallback=False, confidence=1.0)
        if jev is None:
            return PolicyDecision(allowed=True, tier=None, requested_model=request.current_model,
                                  reason="no_jev_fallback", fallback=True, confidence=0.0)
        conf = float(jev.get("confidence", 0.0))
        if conf < self.thresholds["low"]:
            return PolicyDecision(allowed=True, tier=None, requested_model=request.current_model,
                                  reason="low_confidence_keep_current", fallback=True, confidence=conf)
        tier = jev.get("requested_tier")
        model = jev.get("requested_model")
        pressure = 0.0
        if request.context_tokens and request.max_context_tokens:
            pressure = request.context_tokens / max(1, request.max_context_tokens)
        if pressure > 0.9 and tier == "fast" and request.current_model:
            return PolicyDecision(allowed=True, tier=None, requested_model=request.current_model,
                                  reason="context_pressure_block_downgrade", fallback=True, confidence=conf)
        return PolicyDecision(allowed=True, tier=tier, requested_model=model,
                              reason="jev_accepted", fallback=False, confidence=conf)
