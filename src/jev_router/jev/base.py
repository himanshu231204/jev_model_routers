"""Shared client-kind protocol for stdlib vs SDK transports."""
from __future__ import annotations
from typing import Protocol

CLIENT_KINDS = ("stdlib", "sdk")

class JevClientProtocol(Protocol):
    def ask(self, payload: dict) -> tuple: ...

def resolve_client_kind(config: dict, env: dict) -> str:
    raw = (config.get("jev", {}) or {}).get("client", None)
    if raw in CLIENT_KINDS:
        return raw
    if env.get("JEV_CLIENT") in CLIENT_KINDS:
        return env["JEV_CLIENT"]
    return "stdlib"
