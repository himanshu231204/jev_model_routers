"""Routing metrics: decision latency, JEV success, fallback, and override rates."""
from __future__ import annotations
class Metrics:
    def __init__(self):
        self.total = 0; self.fallbacks = 0; self.overrides = 0; self.latencies: list[int] = []
    def record(self, fallback: bool, override: bool, latency_ms: int) -> None:
        self.total += 1; self.fallbacks += fallback; self.overrides += override; self.latencies.append(latency_ms)
    def snapshot(self) -> dict:
        return {"total": self.total, "fallback_rate": self.fallbacks / max(1, self.total),
                "override_rate": self.overrides / max(1, self.total),
                "avg_latency_ms": sum(self.latencies) / max(1, len(self.latencies))}
