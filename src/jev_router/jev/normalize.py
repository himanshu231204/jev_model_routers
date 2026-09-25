"""Normalize external JEV responses at this boundary only.

Expects TypeSafe System One API shape: {"answers": {"tier": {"type": "choice",
"choice": "fast"|"balanced"|"strong", "probabilities": {...}, "confidence": float}}}.
"""
from __future__ import annotations
from jev_router.jev.schema import JEVDecision

def _clamp(v, default=0.0):
    try:
        return max(0.0, min(1.0, float(v)))
    except (TypeError, ValueError):
        return default

def normalize_jev_payload(raw: dict | None, latency_ms: int) -> JEVDecision | None:
    if not isinstance(raw, dict):
        choices = getattr(raw, "choices", None)
        if isinstance(choices, dict) and "tier" in choices:
            ans = choices["tier"]
            choice = getattr(ans, "choice", None)
            conf = getattr(ans, "confidence", 0.0)
            tier = choice if choice in ("fast", "balanced", "strong") else None
            return JEVDecision(requested_model=None, requested_tier=tier,
                               confidence=_clamp(conf), latency_ms=latency_ms, raw_response=None)
        return None
    answers = raw.get("answers", {})
    tier_answer = answers.get("tier", {}) if isinstance(answers, dict) else {}
    choice = tier_answer.get("choice") if isinstance(tier_answer, dict) else None
    tier = choice if choice in ("fast", "balanced", "strong") else None
    return JEVDecision(requested_model=None, requested_tier=tier,
                       confidence=_clamp(tier_answer.get("confidence")),
                       latency_ms=latency_ms, raw_response=None)
