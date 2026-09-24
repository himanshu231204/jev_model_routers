from jev_router.core.router import Router
from jev_router.state.memory import MemoryStore
from jev_router.contracts.models import ModelSpec
from jev_router.adapters.registry import get_adapter

class MockJev:
    def ask(self, payload):
        from jev_router.jev.schema import JEVDecision
        assert "prompt" in payload
        return JEVDecision(requested_tier="balanced", confidence=0.7), 3, None

def test_e2e_fake_agent_router_fake_provider():
    a = get_adapter("opencode")
    n = a.normalize_request({"session_id": "s", "prompt": "add test", "model": "p/fast", "available_models": ["p/fast", "p/balanced"]})
    r = Router(jev_client=MockJev(), store=MemoryStore(),
               candidates=[ModelSpec(id="p/fast", provider="p", tier="fast"), ModelSpec(id="p/balanced", provider="p", tier="balanced")], privacy={})
    d = r.route(n)
    rewritten = a.apply_model({"session_id": "s", "prompt": "x"}, d.final_model)
    assert d.final_model in str(rewritten) and not d.fallback
