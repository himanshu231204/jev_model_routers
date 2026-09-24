"""Claude Code proxy transport that forwards requests while preserving native streaming."""
from __future__ import annotations
class ClaudeProxy:
    def __init__(self, transport):
        self.transport = transport
    def forward(self, request: dict) -> dict:
        return self.transport.send({"path": "/v1/messages", "body": request})
