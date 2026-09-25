"""End-to-end behaviour of the Claude Code "JEV Router" MVP: picker entry, JEV request shape,
per-turn routing through the real proxy against a fake upstream, fail-open, and the
chunked-response / WinError 10054 regression. JEV is mocked here; the opt-in real-API check
lives in ``test_live_jev_api.py``."""
from __future__ import annotations

import http.client
import json
import socket
import struct
import threading
import time
import urllib.error
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from jev_router_live import stdlib_router
from jev_router_live.bin.jev_claude import _auto_model_env
from jev_router_live.config import AUTO_MODEL, JEV_MODEL, Thresholds, id_of
from jev_router_live.proxy import start_proxy
from jev_router_live.stdlib_router import stdlib_ask_jev

FIXTURE = Path(__file__).parent.parent / "fixtures" / "jev_live_response.json"
MODELS = [
    {"id": "claude-haiku-4-5-20251001", "tier": "haiku", "description": "Haiku"},
    {"id": "claude-sonnet-5", "tier": "sonnet", "description": "Sonnet"},
    {"id": "claude-opus-5-5", "tier": "opus", "description": "Opus"},
]


# --- picker ---------------------------------------------------------------------------------


def test_picker_offers_jev_router_row():
    env = _auto_model_env()
    assert env["ANTHROPIC_CUSTOM_MODEL_OPTION"] == AUTO_MODEL
    assert env["ANTHROPIC_CUSTOM_MODEL_OPTION_NAME"] == "JEV Router"


# --- JEV client: auth and request shape -----------------------------------------------------


@pytest.fixture
def captured_post(monkeypatch):
    calls = []

    def fake_post(payload, headers, timeout_s):
        calls.append({"payload": payload, "headers": headers})
        return json.loads(FIXTURE.read_text(encoding="utf-8"))

    monkeypatch.setattr(stdlib_router, "_post", fake_post)
    monkeypatch.setenv("TYPESAFE_API_KEY", "test-key")
    monkeypatch.delenv("JEV_API_KEY", raising=False)
    return calls


def test_request_matches_system_one_schema(captured_post):
    stdlib_ask_jev(prompt="rename x", current="claude-opus-5-5", context_tokens=123, models=MODELS)
    payload = captured_post[0]["payload"]

    assert payload["model"] == JEV_MODEL
    state = payload["state"]
    assert state["request"] == "rename x"
    assert state["session"] == {"current_model": "claude-opus-5-5", "context_tokens": 123}
    assert state["environment"]["available_models"] == [m["id"] for m in MODELS]

    for name in ("task_complexity", "reasoning_required", "tool_complexity"):
        q = payload["questions"][name]
        assert q["type"] == "score" and isinstance(q["instructions"], str)
        assert isinstance(q["criteria"], list) and all(isinstance(c, str) for c in q["criteria"])
    choice = payload["questions"]["model"]
    assert choice["type"] == "choice" and isinstance(choice["instructions"], str)
    assert set(choice["criteria"]) == {m["id"] for m in MODELS}
    assert all(isinstance(v, str) and v for v in choice["criteria"].values())


def test_real_response_is_parsed(captured_post):
    out = stdlib_ask_jev(prompt="rename x", current="claude-opus-5-5", context_tokens=0, models=MODELS)
    assert out["choice"] == "claude-haiku-4-5-20251001"
    assert out["confidence"] == pytest.approx(1.0)
    assert 0 <= out["metrics"]["taskComplexity"] <= 1


def test_typesafe_api_key_is_sent_as_bearer(captured_post):
    stdlib_ask_jev(prompt="x", current="c", context_tokens=0, models=MODELS)
    assert captured_post[0]["headers"]["Authorization"] == "Bearer test-key"


def test_typesafe_api_key_is_required_and_legacy_name_ignored(monkeypatch):
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    monkeypatch.setenv("JEV_API_KEY", "legacy-key")
    monkeypatch.setattr(stdlib_router, "_post", lambda *a: pytest.fail("JEV must not be called"))
    assert stdlib_ask_jev(prompt="x", current="c", context_tokens=0, models=MODELS) is None


def test_key_variable_names_live_only_in_config():
    """One place decides which credential is read, so no module can quietly read another."""
    src = Path(stdlib_router.__file__).parent
    offenders = [
        p.name
        for p in src.rglob("*.py")
        if p.name != "config.py"
        and any(name in p.read_text(encoding="utf-8") for name in ("TYPESAFE_API_KEY", "JEV_API_KEY"))
    ]
    assert offenders == []


# --- JEV client: fail open ------------------------------------------------------------------


def test_timeout_fails_open(monkeypatch):
    monkeypatch.setenv("TYPESAFE_API_KEY", "k")
    monkeypatch.setattr(stdlib_router, "THRESHOLDS", Thresholds(jev_timeout_ms=50, jev_deadline_ms=120))
    monkeypatch.setattr(stdlib_router, "_post", lambda *a: time.sleep(1))
    started = time.time()
    assert stdlib_ask_jev(prompt="x", current="c", context_tokens=0, models=MODELS) is None
    assert time.time() - started < 0.5


def test_5xx_fails_open(monkeypatch):
    monkeypatch.setenv("TYPESAFE_API_KEY", "k")

    def boom(*a):
        raise urllib.error.HTTPError("u", 503, "unavailable", {}, None)

    monkeypatch.setattr(stdlib_router, "_post", boom)
    assert stdlib_ask_jev(prompt="x", current="c", context_tokens=0, models=MODELS) is None


def test_malformed_response_fails_open(monkeypatch):
    monkeypatch.setenv("TYPESAFE_API_KEY", "k")
    monkeypatch.setattr(stdlib_router, "_post", lambda *a: {"answers": {"model": {"choice": "x"}}})
    assert stdlib_ask_jev(prompt="x", current="c", context_tokens=0, models=MODELS) is None


# --- proxy end to end against a fake Anthropic upstream -------------------------------------


class _Upstream:
    """Fake api.anthropic.com: records request bodies and answers /v1/messages with a chunked
    SSE stream, exactly like the real API does."""

    def __init__(self, catalog=None):
        self.bodies: list[dict] = []
        outer = self

        class H(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, *a):
                pass

            def do_GET(self):
                data = json.dumps({"data": catalog or []}).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def do_POST(self):
                outer.bodies.append(json.loads(self.rfile.read(int(self.headers["Content-Length"]))))
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Transfer-Encoding", "chunked")
                self.end_headers()
                for part in (b"event: message_start\ndata: {}\n\n", b"event: message_stop\ndata: {}\n\n"):
                    self.wfile.write(b"%x\r\n%s\r\n" % (len(part), part))
                self.wfile.write(b"0\r\n\r\n")

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), H)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}"

    def close(self):
        self.server.shutdown()
        self.server.server_close()


class _Route:
    def __init__(self, answer):
        self.answer = answer
        self.calls: list[dict] = []

    def __call__(self, **kwargs):
        self.calls.append(kwargs)
        return self.answer


def _jev_answer(choice, confidence=0.95):
    return {"choice": choice, "confidence": confidence, "metrics": {}, "request": {}, "response": {}, "ms": 1}


CATALOG = [{"id": m["id"], "display_name": m["description"]} for m in MODELS]


@pytest.fixture
def rig():
    upstream = _Upstream(CATALOG)
    handles = []

    def make(route):
        handle = start_proxy(upstream_url=upstream.url, route=route)
        handles.append(handle)
        conn = http.client.HTTPConnection("127.0.0.1", handle.port, timeout=5)
        conn.request("GET", "/v1/models")  # Claude Code's gateway model discovery
        conn.getresponse().read()
        return conn

    yield upstream, make
    for h in handles:
        h.close()
    upstream.close()


def _send(conn, body):
    conn.request("POST", "/v1/messages", body=json.dumps(body), headers={"Content-Type": "application/json"})
    resp = conn.getresponse()
    return resp, resp.read()


def _turn(text, model=AUTO_MODEL):
    return {
        "model": model,
        "tools": [{"name": "Bash", "input_schema": {}}],
        "metadata": {"user_id": json.dumps({"session_id": "s1"})},
        "messages": [{"role": "user", "content": text}],
    }


def _continuation(first_text, model=AUTO_MODEL):
    body = _turn(first_text, model)
    body["messages"] += [
        {"role": "assistant", "content": [{"type": "tool_use", "id": "t1", "name": "Bash", "input": {}}]},
        {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "t1", "content": "ok"}]},
    ]
    return body


def test_new_turn_routes_once_and_pins_model_for_tool_calls(rig):
    upstream, make = rig
    route = _Route(_jev_answer("claude-haiku-4-5-20251001"))
    conn = make(route)

    _send(conn, _turn("rename x to count"))
    _send(conn, _continuation("rename x to count"))
    _send(conn, _continuation("rename x to count"))

    assert len(route.calls) == 1
    assert route.calls[0]["prompt"] == "rename x to count"
    assert [m["id"] for m in route.calls[0]["models"]] == [m["id"] for m in MODELS]
    assert [b["model"] for b in upstream.bodies] == ["claude-haiku-4-5-20251001"] * 3


def test_first_turn_large_context_still_downgrades(rig):
    """A fresh conversation's system-prompt-heavy context (~30k tokens here) must not trip the
    cache-rebuild guard: nothing is pinned yet, so Jev's downgrade goes through."""
    upstream, make = rig
    route = _Route(_jev_answer("claude-haiku-4-5-20251001"))
    conn = make(route)

    body = _turn("rename x to count " + "pad " * 30000)
    resp, _ = _send(conn, body)

    assert resp.status == 200
    assert route.calls and route.calls[0]["context_tokens"] > 20_000
    assert upstream.bodies[0]["model"] == "claude-haiku-4-5-20251001"


def test_subsequent_turn_large_context_downgrade_still_blocked(rig):
    """Once a model is pinned, the cache-rebuild guard applies again."""
    upstream, make = rig
    route = _Route(_jev_answer("claude-opus-5-5"))
    conn = make(route)

    text = "pad " * 30000
    _send(conn, _turn(text))

    route.answer = _jev_answer("claude-haiku-4-5-20251001")
    second = _turn(text)
    second["messages"] += [
        {"role": "assistant", "content": "done"},
        {"role": "user", "content": "now rename y to z"},
    ]
    resp, _ = _send(conn, second)

    assert resp.status == 200
    assert len(route.calls) == 2  # fresh turn: Jev asked again...
    assert [b["model"] for b in upstream.bodies] == ["claude-opus-5-5", "claude-opus-5-5"]  # ...but downgrade blocked


def test_explicit_model_passes_through_without_jev(rig):
    upstream, make = rig
    route = _Route(_jev_answer("claude-haiku-4-5-20251001"))
    conn = make(route)

    _send(conn, _turn("do something", model="claude-sonnet-5"))

    assert route.calls == []
    assert upstream.bodies[0]["model"] == "claude-sonnet-5"


@pytest.mark.parametrize(
    "answer",
    [None, _jev_answer("claude-nonexistent-9"), {"garbage": True}],
    ids=["jev-failed", "unavailable-model", "invalid-response"],
)
def test_jev_failure_falls_back_to_a_catalog_model(rig, answer):
    upstream, make = rig
    conn = make(_Route(answer))

    resp, _ = _send(conn, _turn("do something"))

    assert resp.status == 200
    assert upstream.bodies[0]["model"] == "claude-opus-5-5"  # verified catalog id, never the sentinel


def test_catalog_unavailable_falls_back_to_verified_static_id():
    """No /v1/models data at all: the fallback is the static Opus id, which is verified
    against Claude Code 2.1.281's shipped model catalog (claude-opus-5 is its first-party
    Opus 5 id), not an assumed string."""
    from jev_router_live.proxy import fallback_model

    assert fallback_model({}) == "claude-opus-5"


# --- chunked streaming / WinError 10054 regression ------------------------------------------


def _raw_exchange(port, body):
    s = socket.create_connection(("127.0.0.1", port), timeout=3)
    data = json.dumps(body).encode()
    s.sendall(
        b"POST /v1/messages HTTP/1.1\r\nHost: x\r\nContent-Type: application/json\r\n"
        + f"Content-Length: {len(data)}\r\n\r\n".encode()
        + data
    )
    s.settimeout(0.5)
    raw = b""
    try:
        while chunk := s.recv(65536):
            raw += chunk
    except socket.timeout:
        pass
    return s, raw


def test_streamed_response_is_valid_http(rig):
    """The upstream streams with Transfer-Encoding: chunked. Forwarding that header next to a
    Content-Length (with a de-chunked body) is invalid HTTP: Node rejects it
    (HPE_INVALID_CONTENT_LENGTH) and resets the socket, which surfaced as WinError 10054."""
    upstream, make = rig
    conn = make(_Route(_jev_answer("claude-sonnet-5")))
    s, raw = _raw_exchange(conn.port, _turn("x"))
    s.close()
    head = raw.split(b"\r\n\r\n", 1)[0].decode().lower().split("\r\n")
    names = [line.split(":", 1)[0] for line in head[1:]]
    assert not ("content-length" in names and "transfer-encoding" in names)
    assert names.count("date") <= 1 and names.count("server") <= 1

    # And a real HTTP client reads the full SSE body back intact.
    resp, body = _send(conn, _turn("x"))
    assert b"message_start" in body and b"message_stop" in body


def test_client_reset_does_not_print_traceback(capfd):
    handle = start_proxy(upstream_url="http://127.0.0.1:9", route=_Route(None))
    try:
        s = socket.create_connection(("127.0.0.1", handle.port))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack("ii", 1, 0))
        s.close()  # RST, like a client dropping an idle keep-alive socket on Windows
        time.sleep(0.3)
    finally:
        handle.close()
    assert "Traceback" not in capfd.readouterr().err
