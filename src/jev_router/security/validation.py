"""Validation of untrusted external input before it enters the router."""
from __future__ import annotations
def validate_request_shape(raw: dict) -> bool:
    return isinstance(raw, dict) and bool(raw.get("session_id")) and isinstance(raw.get("prompt", ""), str)
