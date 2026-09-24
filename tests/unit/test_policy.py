# tests/unit/test_policy.py
from jev_router.core.policy import Policy
from jev_router.contracts.requests import NormalizedRequest
from jev_router.core.overrides import UserOverride

def _req(**kw):
    base = dict(request_id="r", agent="a", session_id="s", conversation_id="c",
                turn_id="t", prompt="hi", messages=[], available_models=["m1", "m2"],
                tools=[], tool_count=0, context_tokens=1000, max_context_tokens=100000, metadata={})
    base.update(kw)
    return NormalizedRequest(**base)

def _jev(**kw):
    d = dict(requested_model=None, requested_tier="strong", confidence=0.9)
    d.update(kw)
    return d

def test_override_wins():
    p = Policy({"low": 0.3, "medium": 0.6, "high": 0.85})
    dec = p.evaluate(_req(), _jev(), UserOverride(kind="tier", value="fast"))
    assert dec.tier == "fast" and dec.reason == "explicit_override"

def test_low_confidence_preserves_current():
    p = Policy({"low": 0.3, "medium": 0.6, "high": 0.85})
    dec = p.evaluate(_req(current_model="m1"), _jev(confidence=0.1), None)
    assert dec.tier is None and dec.reason == "low_confidence_keep_current"

def test_large_context_blocks_downgrade():
    p = Policy({"low": 0.3, "medium": 0.6, "high": 0.85})
    dec = p.evaluate(_req(current_model="strong-m", context_tokens=95000, max_context_tokens=100000),
                     _jev(requested_tier="fast", confidence=0.5), None)
    assert dec.reason == "context_pressure_block_downgrade"
