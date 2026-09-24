import sys, types


def test_sdk_client_maps_choice_to_decision(monkeypatch):
    import os
    monkeypatch.setenv("TYPESAFE_API_KEY", "test-key")
    fake = types.ModuleType("typesafe_sdk")

    class FakeChoice:
        def __init__(self, instructions=None, criteria=None):
            self.instructions = instructions; self.criteria = criteria

    class FakeAnswer:
        choice = "strong"; confidence = 0.97; probabilities = {}

    class FakeResult:
        choices = {"tier": FakeAnswer()}

    class FakeClient:
        def __init__(self, api_key=None, base_url=None, model=None, retry=None):
            pass
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def system_one(self, state, questions, **kw):
            assert "tier" in questions
            return FakeResult()
    fake.Choice = FakeChoice; fake.TypeSafeClient = FakeClient
    fake.RetryPolicy = lambda **kw: kw
    monkeypatch.setitem(sys.modules, "typesafe_sdk", fake)
    from jev_router.jev.sdk_client import SdkJevClient
    dec, ms, err = SdkJevClient(timeout_ms=500, deadline_ms=2000, max_retries=0).ask(
        {"model": "jev-latest", "state": {"prompt": "hi"}, "questions": {"tier": {"type": "choice", "instructions": "pick", "criteria": {"fast": None, "balanced": None, "strong": None}}}})
    assert err is None and dec.requested_tier == "strong" and dec.confidence == 0.97
