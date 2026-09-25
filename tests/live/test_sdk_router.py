def test_live_sdk_router_returns_same_shape(monkeypatch):
    import sys, types
    fake = types.ModuleType("typesafe_sdk")
    class FakeChoice:
        def __init__(self, **kw): pass
    class FakeScore:
        def __init__(self, **kw): pass
    class FakeModelAns:
        choice = "claude-sonnet-5"; confidence = 0.9; probabilities = {}
    class FakeScoreAns:
        score = 5
    class FakeResult:
        choices = {"model": FakeModelAns()}
        scores = {"task_complexity": FakeScoreAns(), "reasoning_required": FakeScoreAns(), "tool_complexity": FakeScoreAns()}
    class FakeClient:
        def __init__(self, **kw): pass
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def system_one(self, state, questions, **kw): return FakeResult()
    fake.Choice = FakeChoice; fake.Score = FakeScore
    fake.TypeSafeClient = FakeClient; fake.RetryPolicy = lambda **kw: kw
    monkeypatch.setitem(sys.modules, "typesafe_sdk", fake)
    monkeypatch.setenv("JEV_API_KEY", "k")
    monkeypatch.setenv("JEV_CLIENT", "sdk")
    from jev_router_live.sdk_router import sdk_ask_jev
    out = sdk_ask_jev(prompt="fix bug", current="haiku", context_tokens=100,
                      models=[{"id": "claude-sonnet-5", "tier": "sonnet"}])
    assert out["choice"] == "claude-sonnet-5" and out["ms"] >= 0
    assert out["request"]["state"]["request"] == "fix bug"
    assert out["request"]["questions"]["model"]
