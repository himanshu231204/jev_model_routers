"""Normalize external JEV responses at this boundary only."""
from __future__ import annotations
from jev_router.jev.schema import JEVDecision

def _clamp(v, default=0.0):
    try:
        return max(0.0, min(1.0, float(v)))
    except (TypeError, ValueError):
        return default

def normalize_jev_payload(raw: dict | None, latency_ms: int) -> JEVDecision | None:
    if not isinstance(raw, dict):
        return None
    choice = raw.get("choice") or raw.get("selected_model") or raw.get("tier")
    m = raw.get("metrics", {}) if isinstance(raw.get("metrics"), dict) else {}
    tier = choice if choice in ("fast", "balanced", "strong") else None
    model = choice if tier is None and isinstance(choice, str) else None
    return JEVDecision(requested_model=model, requested_tier=tier,
                       confidence=_clamp(raw.get("confidence")),
                       task_complexity=_clamp(m.get("task_complexity")),
                       reasoning_required=_clamp(m.get("reasoning_required")),
                       tool_complexity=_clamp(m.get("tool_complexity")),
                       context_pressure=_clamp(m.get("context_size")),
                       latency_ms=latency_ms, raw_response=None)
