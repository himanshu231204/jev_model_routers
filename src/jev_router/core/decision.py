"""Normalized routing decision contract and its explainability representation."""
from __future__ import annotations
from dataclasses import dataclass

@dataclass
class PolicyDecision:
    allowed: bool = True
    tier: str | None = None
    requested_model: str | None = None
    reason: str = "default"
    fallback: bool = False
    confidence: float = 0.0

@dataclass
class ModelResolution:
    model: str
    reason: str = "resolved"
    fallback: bool = False

@dataclass
class RoutingDecision:
    final_model: str
    reason: str = "default"
    changed: bool = False
    fallback: bool = False
    confidence: float | None = None
    pinned_until: str | None = None

    def explain(self) -> str:
        return f"model={self.final_model} reason={self.reason} fallback={self.fallback} confidence={self.confidence}"
