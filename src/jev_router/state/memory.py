"""In-memory routing state store for ephemeral sessions."""
from __future__ import annotations
from jev_router.core.lifecycle import TurnState

class MemoryStore:
    def __init__(self):
        self._data: dict[str, TurnState] = {}
    def pin(self, key: str, state: TurnState) -> None:
        self._data[key] = state
    def get(self, key: str) -> TurnState | None:
        return self._data.get(key)
    def clear(self, key: str) -> None:
        self._data.pop(key, None)
