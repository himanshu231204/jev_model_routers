"""Minimal JEV routing payload builder honoring privacy flags.

Payload shape matches OpenRouter's Decisions API (POST /api/alpha/decisions):
{"model": ..., "state": {...turn context...}, "questions": {...typed questions...}}.
"""
from __future__ import annotations
from jev_router.contracts.requests import NormalizedRequest

_MODEL = "typesafe/jev-1.13"

_TIER_QUESTION = {
    "type": "choice",
    "instructions": "Given the coding task described in state, pick the model tier "
                     "that best balances capability and cost for this turn.",
    "criteria": {
        "fast": "Simple, low-risk task: trivial edits, lookups, or well-defined mechanical changes.",
        "balanced": "Moderate task: typical feature work or bug fixes with some ambiguity.",
        "strong": "Complex task: deep reasoning, architecture, or high-risk changes.",
    },
}

def build_jev_payload(request: NormalizedRequest, privacy: dict) -> dict:
    state: dict = {"prompt": request.prompt, "current_model": request.current_model,
                   "available_models": list(request.available_models or []),
                   "context_tokens": request.context_tokens,
                   "tool_count": request.tool_count,
                   "tools": [{"name": t.name, "category": t.category} for t in request.tools]}
    if privacy.get("send_repository_content") and request.repository:
        state["repository"] = {"language": request.repository.language, "project_type": request.repository.project_type}
    return {"model": _MODEL, "state": state, "questions": {"tier": _TIER_QUESTION}}
