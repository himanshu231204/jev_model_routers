"""JEV decision contract normalized at the external boundary."""
from __future__ import annotations
from dataclasses import dataclass

@dataclass
class JEVDecision:
    requested_model: str | None = None
    requested_tier: str | None = None
    confidence: float = 0.0
    task_complexity: float = 0.0
    reasoning_required: float = 0.0
    tool_complexity: float = 0.0
    context_pressure: float = 0.0
    latency_ms: int = 0
    raw_response: dict | None = None
