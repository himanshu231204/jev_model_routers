import os
from jev_router.jev.normalize import normalize_jev_payload
from jev_router.jev.questions import build_jev_payload
from jev_router.contracts.requests import NormalizedRequest

def test_normalize_clamps_confidence():
    d = normalize_jev_payload({"choice": "strong", "confidence": 9, "metrics": {}}, 10)
    assert 0.0 <= d.confidence <= 1.0 and d.requested_tier == "strong"

def test_payload_minimal_by_default():
    r = NormalizedRequest(request_id="r", agent="a", session_id="s", conversation_id="c",
                          turn_id="t", prompt="secret prompt", messages=[],
                          available_models=["m"], tools=[], tool_count=0, metadata={})
    p = build_jev_payload(r, {"send_repository_content": False})
    assert p["prompt"] == "secret prompt" and "repository" not in p

def test_client_missing_key_returns_error():
    from jev_router.jev.client import JevClient
    os.environ.pop("JEV_API_KEY", None)
    c = JevClient(timeout_ms=100, deadline_ms=200, max_retries=0)
    dec, ms, err = c.ask({"prompt": "hi"})
    assert dec is None and err is not None
