"""Structured observability event contract for routing decisions and metrics."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


@dataclass
class RoutingEvent:
    event: str = "routing.decision"
    request_id: str = ""
    agent: str = ""
    session_id: str = ""
    turn_id: str = ""
    current_model: str | None = None
    selected_model: str | None = None
    confidence: float | None = None
    reason: str = ""
    jev_latency_ms: int = 0
    fallback: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)
