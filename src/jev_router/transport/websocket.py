"""WebSocket placeholder over stdlib: frames via http upgrade not implemented; raises with clear message."""
from __future__ import annotations
class WebsocketTransport:
    def __init__(self, url: str):
        self.url = url
    def send(self, request: dict) -> dict:
        raise NotImplementedError("websocket transport requires explicit opt-in; use HTTP/SSE proxy by default")
