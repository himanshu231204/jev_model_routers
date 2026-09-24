from __future__ import annotations
from jev_router.contracts.requests import NormalizedRequest, Message
def parse(raw: dict) -> NormalizedRequest:
    text = raw.get("input_text", "") or " ".join(m.get("content", "") for m in raw.get("messages", []))
    return NormalizedRequest(request_id="req_codex", agent="codex", session_id=raw.get("session_id", ""),
                             conversation_id=raw.get("session_id", ""), turn_id="t1", prompt=text,
                             messages=[Message(role="user", content=text)], current_model=raw.get("model"),
                             available_models=raw.get("available_models", [raw.get("model", "")]),
                             tools=[], tool_count=0, metadata={"tool_result": bool(raw.get("tool_result", False))})
