"""SSE line parser over a streamed HTTP body (stdlib only)."""
from __future__ import annotations
def parse_sse(text: str) -> list[dict]:
    events = []
    for chunk in text.split("\n\n"):
        data = "".join(l[5:] for l in chunk.splitlines() if l.startswith("data:"))
        if data.strip():
            events.append({"data": data.strip()})
    return events

class SseTransport:
    def __init__(self, inner):
        self.inner = inner
    def send(self, request: dict) -> dict:
        raw = self.inner.send(request)
        return {**raw, "events": parse_sse(raw.get("body", ""))}
