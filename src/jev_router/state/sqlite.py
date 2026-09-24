"""SQLite-backed routing state store for durable sessions."""
from __future__ import annotations
import sqlite3
from jev_router.core.lifecycle import TurnState

_SCHEMA = "CREATE TABLE IF NOT EXISTS turns (k TEXT PRIMARY KEY, turn_id TEXT, model TEXT, tier TEXT, created_at REAL, reason TEXT, confidence REAL)"

class SqliteStore:
    def __init__(self, path: str):
        self.path = path
        with sqlite3.connect(path) as c:
            c.execute(_SCHEMA)
    def pin(self, key: str, state: TurnState) -> None:
        with sqlite3.connect(self.path) as c:
            c.execute("REPLACE INTO turns VALUES (?,?,?,?,?,?,?)",
                      (key, state.turn_id, state.model, state.tier, state.created_at, state.reason, state.confidence))
    def get(self, key: str) -> TurnState | None:
        with sqlite3.connect(self.path) as c:
            row = c.execute("SELECT turn_id, model, tier, created_at, reason, confidence FROM turns WHERE k=?", (key,)).fetchone()
        return TurnState(*row) if row else None
    def clear(self, key: str) -> None:
        with sqlite3.connect(self.path) as c:
            c.execute("DELETE FROM turns WHERE k=?", (key,))
