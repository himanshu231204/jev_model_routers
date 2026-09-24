"""Redaction of secrets and prompt content from logs and diagnostics."""
from __future__ import annotations
import copy
_SENSITIVE_KEYS = {"authorization", "api_key", "api-key", "jev_api_key", "token", "cookie", "prompt", "messages", "raw_response"}

def redact(obj: dict, log_prompts: bool = False) -> dict:
    out = copy.deepcopy(obj)
    for k in list(out.keys()):
        if k.lower() in _SENSITIVE_KEYS and not (k == "prompt" and log_prompts):
            out[k] = "<redacted>"
    return out
