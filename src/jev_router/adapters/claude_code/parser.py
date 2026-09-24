"""Parser converting Claude Code request and response payloads to and from normalized contracts."""
from __future__ import annotations
from jev_router.contracts.requests import NormalizedRequest, Message
def parse(raw: dict) -> NormalizedRequest:
    msgs = [Message(role=m.get("role", "user"), content=str(m.get("content", ""))) for m in raw.get("messages", [])]
    prompt = next((m.content for m in reversed(msgs) if m.role == "user"), "")
    return NormalizedRequest(request_id=raw.get("request_id", "req_claude"), agent="claude_code",
                             agent_version=raw.get("agent_version"), session_id=raw.get("session_id", ""),
                             conversation_id=raw.get("session_id", ""), turn_id=raw.get("turn_id", "t1"),
                             prompt=prompt, messages=msgs, current_model=raw.get("model"),
                             available_models=raw.get("available_models", [raw.get("model", "")]),
                             tools=[], tool_count=len(raw.get("tools", [])),
                             stream=bool(raw.get("stream", False)), is_new_turn="tool_calls" not in str(raw.get("messages", "")),
                             metadata={"kind": raw.get("kind", ""), "tool_result": bool(raw.get("tool_result", False))})
