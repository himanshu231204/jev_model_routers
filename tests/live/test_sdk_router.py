"""The opt-in SDK client (JEV_CLIENT=sdk), exercised with the real ``typesafe-sdk`` against a
local System One stand-in, so retry, timeout and parsing behaviour is the SDK's own."""
import json
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from jev_router_live import stdlib_router
from jev_router_live.config import THRESHOLDS
from jev_router_live.sdk_router import sdk_ask_jev

MODELS = [{"id": "claude-haiku-4-5-20251001", "tier": "haiku"}, {"id": "claude-sonnet-5", "tier": "sonnet"}]


def _score(value):
    return {"type": "score", "score": value, "confidence": 0.8,
            "legend": {"0": "None", "9": "Extreme"}, "probabilities": {"0": 0.5, "9": 0.5}}


OK_BODY = {
    "model": "jev-1.13.0",
    "answers": {
        "task_complexity": _score(4.5),
        "reasoning_required": _score(9.0),
        "tool_complexity": _score(0.0),
        "model": {"type": "choice", "choice": "claude-sonnet-5", "confidence": 0.62,
                  "probabilities": {"claude-haiku-4-5-20251001": 0.2, "claude-sonnet-5": 0.8}},
    },
    "usage": {"input_tokens": 300, "output_tokens": 40},
}


@pytest.fixture
def jev_server(monkeypatch):
    """A System One stand-in answering with a scripted list of (status, delay_s, body)."""
    pytest.importorskip("typesafe_sdk")
    script: list = []
    hits: list[dict] = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            hits.append({"path": self.path, "auth": self.headers.get("Authorization"),
                         "body": json.loads(self.rfile.read(int(self.headers["Content-Length"])))})
            status, delay, body = script[min(len(hits), len(script)) - 1]
            time.sleep(delay)
            data = json.dumps(body).encode()
            try:
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            except OSError:
                pass  # the client gave up (timeout test)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.daemon_threads = True
    threading.Thread(target=server.serve_forever, daemon=True).start()
    monkeypatch.setattr(stdlib_router, "_ENDPOINT", f"http://127.0.0.1:{server.server_address[1]}/v1/systemone")
    monkeypatch.setenv("TYPESAFE_API_KEY", "test-key")
    yield script, hits
    server.shutdown()
    server.server_close()


def _ask():
    return sdk_ask_jev(prompt="fix the flaky test", current="claude-opus-5", context_tokens=100, models=MODELS)


def test_sdk_client_returns_the_stdlib_shape_with_real_scores(jev_server):
    script, hits = jev_server
    script.append((200, 0, OK_BODY))
    out = _ask()
    assert out["choice"] == "claude-sonnet-5"
    assert out["confidence"] == 0.62
    assert out["probabilities"] == {"claude-haiku-4-5-20251001": 0.2, "claude-sonnet-5": 0.8}
    assert out["metrics"]["taskComplexity"] == 0.5
    assert out["metrics"]["reasoningRequired"] == 1.0
    assert out["metrics"]["toolComplexity"] == 0.0
    assert out["response"] == OK_BODY
    assert out["request"]["model"] == "jev-latest"
    assert out["request"]["state"]["request"] == "fix the flaky test"
    # Wire format per TypeSafe's docs: bearer auth, one POST to /v1/systemone, typed questions.
    (hit,) = hits
    assert hit["path"] == "/v1/systemone" and hit["auth"] == "Bearer test-key"
    assert hit["body"]["model"] == "jev-latest"
    assert hit["body"]["questions"]["model"]["type"] == "choice"
    assert set(hit["body"]["questions"]["model"]["criteria"]) == {m["id"] for m in MODELS}
    assert hit["body"]["questions"]["task_complexity"]["type"] == "score"


def test_sdk_client_retries_a_5xx_once(jev_server):
    script, hits = jev_server
    script += [(503, 0, {"error": "busy"}), (200, 0, OK_BODY)]
    assert _ask()["choice"] == "claude-sonnet-5"
    assert len(hits) == 2


@pytest.mark.parametrize("status", [400, 401, 408, 429])
def test_sdk_client_does_not_retry_4xx(jev_server, status):
    """The SDK's defaults would retry 408/429 and honor Retry-After; routing must not."""
    script, hits = jev_server
    script.append((status, 0, {"error": "no"}))
    assert _ask() is None
    assert len(hits) == 1


def test_sdk_client_gives_up_at_the_routing_deadline(jev_server):
    """The SDK's default per-request timeout is 10 s; routing must fail open within 3 s."""
    script, _ = jev_server
    script.append((200, 10, OK_BODY))
    started = time.time()
    assert _ask() is None
    assert time.time() - started < THRESHOLDS.jev_deadline_ms / 1000.0 + 0.5


def test_sdk_client_fails_open_on_a_malformed_answer(jev_server):
    script, _ = jev_server
    body = json.loads(json.dumps(OK_BODY))
    del body["answers"]["tool_complexity"]
    script.append((200, 0, body))
    assert _ask() is None


def test_sdk_client_without_the_sdk_installed_fails_open(monkeypatch):
    monkeypatch.setitem(sys.modules, "typesafe_sdk", None)  # makes the import raise ImportError
    monkeypatch.setenv("TYPESAFE_API_KEY", "k")
    assert _ask() is None


def test_fake_jev_answers_in_a_shape_the_sdk_accepts(monkeypatch):
    """scripts/fake_jev.py stands in for the real API in end-to-end runs; its answers must pass
    the SDK's validation like the captured real response does (it once lacked `usage`)."""
    pytest.importorskip("typesafe_sdk")
    import importlib.util
    from pathlib import Path

    spec = importlib.util.spec_from_file_location("fake_jev", Path(__file__).parents[2] / "scripts" / "fake_jev.py")
    fake_jev = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fake_jev)
    server = ThreadingHTTPServer(("127.0.0.1", 0), fake_jev.Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    monkeypatch.setattr(stdlib_router, "_ENDPOINT", f"http://127.0.0.1:{server.server_address[1]}/v1/systemone")
    monkeypatch.setenv("TYPESAFE_API_KEY", "local")
    try:
        out = sdk_ask_jev(prompt="RENAME x to y", current="claude-opus-5", context_tokens=10, models=MODELS)
    finally:
        server.shutdown()
        server.server_close()
    assert out["choice"] == MODELS[0]["id"]
    assert out["metrics"]["reasoningRequired"] == 1.5 / 9
