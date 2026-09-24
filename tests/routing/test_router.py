from jev_router.core.router import Router
from jev_router.contracts.requests import NormalizedRequest
from jev_router.state.memory import MemoryStore

class FakeJev:
    def ask(self, payload):
        from jev_router.jev.schema import JEVDecision
        return JEVDecision(requested_tier="strong", confidence=0.9), 5, None

def _req(**kw):
    base = dict(request_id="r1", agent="claude_code", session_id="s", conversation_id="c",
                turn_id="t1", prompt="hard refactor", messages=[], current_model="a/fast",
                available_models=["a/fast", "a/strong"], tools=[], tool_count=0,
                context_tokens=100, max_context_tokens=100000, metadata={})
    base.update(kw)
    return NormalizedRequest(**base)

def test_routes_and_pins_tool_loop():
    from jev_router.contracts.models import ModelSpec
    r = Router(jev_client=FakeJev(), store=MemoryStore(),
               candidates=[ModelSpec(id="a/fast", provider="a", tier="fast"),
                           ModelSpec(id="a/strong", provider="a", tier="strong")], privacy={})
    d1 = r.route(_req())
    assert d1.final_model == "a/strong"
    d2 = r.route(_req(is_new_turn=False, metadata={"tool_result": True}))
    assert d2.final_model == "a/strong" and not d2.changed

def test_core_imports_only_contracts():
    import ast, pathlib
    tree = ast.parse(pathlib.Path("src/jev_router/core/router.py").read_text())
    mods = [n.module or "" for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)]
    assert not any(m.startswith("jev_router.adapters") or m.startswith("jev_router.providers") for m in mods)

def test_empty_candidates_no_current_model_fails_open():
    # Fail-open invariant: resolver's terminal ValueError must never propagate;
    # router returns a fallback decision with reason "no_candidates" instead.
    r = Router(jev_client=FakeJev(), store=MemoryStore(), candidates=[], privacy={})
    d = r.route(_req(current_model=None, available_models=[]))
    assert d.reason == "no_candidates" and d.fallback and d.final_model == ""
