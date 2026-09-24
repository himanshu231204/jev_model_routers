from jev_router.core.classifier import RequestKind, classify
from jev_router.contracts.requests import NormalizedRequest

def _req(**kw):
    base = dict(request_id="r", agent="a", session_id="s", conversation_id="c",
                turn_id="t", prompt="hi", messages=[], available_models=[],
                tools=[], tool_count=0, metadata={})
    base.update(kw)
    return NormalizedRequest(**base)

def test_fresh_turn():
    assert classify(_req(is_new_turn=True)) == RequestKind.FRESH_TURN

def test_tool_continuation_bypasses():
    assert classify(_req(is_new_turn=False, metadata={"tool_result": True})) == RequestKind.TOOL_CONTINUATION

def test_auxiliary_bypasses():
    assert classify(_req(is_new_turn=False, metadata={"kind": "summary"})) == RequestKind.AUXILIARY
