from jev_router.contracts.requests import NormalizedRequest
from jev_router.contracts.models import ModelSpec


def test_normalized_request_nullable_optionals():
    r = NormalizedRequest(
        request_id="req_1", agent="claude_code", agent_version=None,
        session_id="s1", conversation_id="c1", turn_id="t1",
        prompt="rename variable", messages=[],
        current_model="balanced", available_models=["m1"],
        tools=[], tool_count=0, context_tokens=None,
        max_context_tokens=None, repository=None, environment=None,
        stream=False, is_subagent=False, is_new_turn=True, metadata={},
    )
    assert r.context_tokens is None
    assert r.repository is None


def test_model_spec_capabilities():
    from jev_router.contracts.models import ModelCapabilities
    caps = ModelCapabilities(coding=9, reasoning=8, tool_use=10, context=9, speed=8, cost=6)
    assert caps.coding == 9
