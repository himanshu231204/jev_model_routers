from jev_router.core.resolver import ModelResolver
from jev_router.core.decision import PolicyDecision
from jev_router.contracts.models import ModelSpec, ModelCapabilities
from jev_router.contracts.requests import NormalizedRequest

def _req(**kw):
    base = dict(request_id="r", agent="claude_code", session_id="s", conversation_id="c",
                turn_id="t", prompt="hi", messages=[], current_model="a/m1",
                available_models=["a/m1", "a/m2"], tools=[], tool_count=0, metadata={})
    base.update(kw)
    return NormalizedRequest(**base)

def test_exact_model_available():
    r = ModelResolver()
    cands = [ModelSpec(id="a/m1", provider="a"), ModelSpec(id="a/m2", provider="a")]
    out = r.resolve(_req(), PolicyDecision(requested_model="a/m2", reason="explicit_override"), cands)
    assert out.model == "a/m2" and not out.fallback

def test_tier_maps_to_best_coding():
    r = ModelResolver()
    cands = [ModelSpec(id="a/m1", provider="a", tier="fast", capabilities=ModelCapabilities(coding=4)),
             ModelSpec(id="a/m2", provider="a", tier="strong", capabilities=ModelCapabilities(coding=9))]
    out = r.resolve(_req(), PolicyDecision(tier="strong", reason="jev_accepted"), cands)
    assert out.model == "a/m2"

def test_unknown_falls_back_to_current():
    r = ModelResolver()
    cands = [ModelSpec(id="a/m1", provider="a")]
    out = r.resolve(_req(current_model="a/m1"), PolicyDecision(requested_model="nope", reason="x"), cands)
    assert out.model == "a/m1" and out.fallback
