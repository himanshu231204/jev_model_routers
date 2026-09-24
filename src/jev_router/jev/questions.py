"""Minimal JEV routing payload builder honoring privacy flags."""
from __future__ import annotations
from jev_router.contracts.requests import NormalizedRequest

def build_jev_payload(request: NormalizedRequest, privacy: dict) -> dict:
    payload: dict = {"prompt": request.prompt, "current_model": request.current_model,
                     "available_models": list(request.available_models or []),
                     "context_tokens": request.context_tokens,
                     "tool_count": request.tool_count,
                     "tools": [{"name": t.name, "category": t.category} for t in request.tools]}
    if privacy.get("send_repository_content") and request.repository:
        payload["repository"] = {"language": request.repository.language, "project_type": request.repository.project_type}
    return payload
