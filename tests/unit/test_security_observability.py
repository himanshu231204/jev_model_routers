from jev_router.security.redaction import redact
from jev_router.security.validation import validate_request_shape
from jev_router.observability.metrics import Metrics

def test_redact_hides_key_and_prompt():
    out = redact({"Authorization": "Bearer x", "prompt": "hello", "model": "m"})
    assert "x" not in str(out) and out["prompt"] == "<redacted>"

def test_validate_rejects_empty():
    assert validate_request_shape({}) is False
    assert validate_request_shape({"session_id": "s", "prompt": "hi"}) is True

def test_metrics_counts_fallback():
    m = Metrics()
    m.record(fallback=True, override=False, latency_ms=10)
    assert m.snapshot()["fallback_rate"] == 1.0
