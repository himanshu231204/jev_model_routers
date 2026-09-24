"""Transport protocol for forwarding provider requests."""
from __future__ import annotations
from typing import Protocol
class Transport(Protocol):
    def send(self, request: dict) -> dict: ...
