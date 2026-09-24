"""Generic credential storage and redaction mechanics; TYPESAFE_API_KEY is read only by the JEV client layer, never here."""
from __future__ import annotations
import os
def get_secret(name: str) -> str | None:
    if name == "TYPESAFE_API_KEY":
        raise RuntimeError("TYPESAFE_API_KEY must be read only via jev.client")
    return os.environ.get(name)
