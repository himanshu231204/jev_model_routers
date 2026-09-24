import os
from jev_router.jev.normalize import normalize_jev_payload
from jev_router.jev.questions import build_jev_payload
from jev_router.contracts.requests import NormalizedRequest

def test_normalize_clamps_confidence():
    raw = {"answers": {"tier": {"type": "choice", "choice": "strong", "confidence": 9}}}
    d = normalize_jev_payload(raw, 10)
    assert 0.0 <= d.confidence <= 1.0 and d.requested_tier == "strong"

def test_normalize_unknown_choice_is_none():
    raw = {"answers": {"tier": {"type": "choice", "choice": "bogus", "confidence": 0.5}}}
    d = normalize_jev_payload(raw, 10)
    assert d.requested_tier is None

def test_payload_minimal_by_default():
    r = NormalizedRequest(request_id="r", agent="a", session_id="s", conversation_id="c",
                          turn_id="t", prompt="secret prompt", messages=[],
                          available_models=["m"], tools=[], tool_count=0, metadata={})
    p = build_jev_payload(r, {"send_repository_content": False})
    assert p["model"] and p["questions"]["tier"]["type"] == "choice"
    assert p["state"]["prompt"] == "secret prompt" and "repository" not in p["state"]

def test_payload_includes_repository_when_enabled():
    from jev_router.contracts.requests import RepositoryContext
    r = NormalizedRequest(request_id="r", agent="a", session_id="s", conversation_id="c",
                          turn_id="t", prompt="p", messages=[], available_models=["m"],
                          tools=[], tool_count=0, metadata={},
                          repository=RepositoryContext(language=["python"], project_type="lib"))
    p = build_jev_payload(r, {"send_repository_content": True})
    assert p["state"]["repository"] == {"language": ["python"], "project_type": "lib"}

def test_client_missing_key_returns_error():
    from jev_router.jev.client import JevClient
    os.environ.pop("TYPESAFE_API_KEY", None)
    c = JevClient(timeout_ms=100, deadline_ms=200, max_retries=0)
    dec, ms, err = c.ask({"prompt": "hi"})
    assert dec is None and err is not None
