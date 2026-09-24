"""Tracing across adapter, router, and provider boundaries."""
from __future__ import annotations
import time, uuid
class Trace:
    def __init__(self, name: str):
        self.id = uuid.uuid4().hex[:8]; self.name = name; self.start = time.time(); self.spans: list[dict] = []
    def span(self, label: str) -> dict:
        s = {"label": label, "at_ms": int((time.time() - self.start) * 1000)}; self.spans.append(s); return s
