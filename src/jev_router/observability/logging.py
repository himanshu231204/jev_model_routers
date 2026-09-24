"""Structured, privacy-safe logging for router events."""
from __future__ import annotations
import json
from jev_router.security.redaction import redact
def log_event(event, log_prompts: bool = False) -> str:
    line = json.dumps(redact(event.__dict__, log_prompts=log_prompts), default=str)
    print(line)
    return line
