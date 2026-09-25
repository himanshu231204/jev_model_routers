"""Production-hardening regressions for the Claude Code proxy: model-catalog self-fetch,
incremental streaming, upstream-vs-client connection failures, safe decision logging,
launcher wiring, and conversation isolation. JEV is mocked; the upstream is a local fake."""
from __future__ import annotations

import http.client
import json
import os
import socket
import struct
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from jev_router_live import proxy as proxy_mod
from jev_router_live.config import AUTO_MODEL, id_of
from jev_router_live.proxy import start_proxy

CATALOG = [
    {"id": "claude-opus-5-5", "display_name": "Opus 5.5"},
    {"id": "claude-sonnet-5", "display_name": "Sonnet 5"},
    {"id": "claude-haiku-4-5-20251001", "display_name": "Haiku 4.5"},
]


class FakeAnthropic:
    """Minimal api.anthropic.com. ``on_post`` decides how /v1/messages answers."""

    def __init__(self, on_post=None, models_status=200):
        self.gets: list[tuple[str, dict]] = []
        self.bodies: list[dict] = []
        outer = self

        class H(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, *a):
                pass

            def do_GET(self):
                outer.gets.append((self.path, {k.lower(): v for k, v in self.headers.items()}))
                data = json.dumps({"data": CATALOG}).encode() if models_status == 200 else b'{"error":{}}'
                self.send_response(models_status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def do_POST(self):
                outer.bodies.append(json.loads(self.rfile.read(int(self.headers["Content-Length"]))))
                (on_post or _plain_json)(self)

        self.server = _QuietServer(("127.0.0.1", 0), H)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}"

    def close(self):
        self.server.shutdown()
        self.server.server_close()


class _QuietServer(ThreadingHTTPServer):
    def handle_error(self, request, client_address):
        pass  # The fake's own teardown noise (e.g. after a deliberate reset) is not under test.


def _plain_json(h):
    data = b'{"type":"message","content":[]}'
    h.send_response(200)
    h.send_header("Content-Type", "application/json")
    h.send_header("Content-Length", str(len(data)))
    h.end_headers()
    h.wfile.write(data)


class Route:
    def __init__(self, choice="claude-sonnet-5", confidence=0.9):
        self.choice, self.confidence = choice, confidence
        self.calls: list[dict] = []

    def __call__(self, **kw):
        self.calls.append(kw)
        return {"choice": self.choice, "confidence": self.confidence, "metrics": {}, "request": {}, "response": {}, "ms": 7}


def _turn(text, session="s1", model=AUTO_MODEL, first=None):
    messages = [{"role": "user", "content": first}] if first else []
    messages.append({"role": "user", "content": text})
    return {
        "model": model,
        "tools": [{"name": "Bash", "input_schema": {}}],
        "metadata": {"user_id": json.dumps({"session_id": session})},
        "messages": messages,
    }


def _post(port, body, headers=None):
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    conn.request("POST", "/v1/messages", body=json.dumps(body), headers={"Content-Type": "application/json", **(headers or {})})
    resp = conn.getresponse()
    data = resp.read()
    conn.close()
    return resp, data


@pytest.fixture
def world():
    made = []

    def make(route, **upstream_kw):
        upstream = FakeAnthropic(**upstream_kw)
        handle = start_proxy(upstream_url=upstream.url, route=route)
        made.append((upstream, handle))
        return upstream, handle

    yield make
    for upstream, handle in made:
        handle.close()
        upstream.close()


# --- model catalog ---------------------------------------------------------------------------


def test_catalog_is_fetched_with_claude_codes_own_credentials(world):
    route = Route()
    upstream, handle = world(route)

    _post(handle.port, _turn("rename x"), headers={"Authorization": "Bearer oauth-token", "anthropic-version": "2023-06-01"})

    assert len(upstream.gets) == 1
    path, headers = upstream.gets[0]
    assert path == "/v1/models?limit=1000"
    assert headers["authorization"] == "Bearer oauth-token"
    assert headers["anthropic-version"] == "2023-06-01"
    # JEV chose among the account's exact catalog ids, not the static fallbacks.
    assert {m["id"] for m in route.calls[0]["models"]} == {m["id"] for m in CATALOG}


def test_catalog_fetch_happens_at_most_once(world):
    upstream, handle = world(Route())
    _post(handle.port, _turn("one", session="a"))
    _post(handle.port, _turn("two", session="b"))
    assert len(upstream.gets) == 1


def test_catalog_failure_falls_back_to_verified_static_ids(world):
    route = Route(choice=id_of("sonnet"))
    upstream, handle = world(route, models_status=404)

    resp, _ = _post(handle.port, _turn("rename x"))

    assert resp.status == 200
    assert {m["id"] for m in route.calls[0]["models"]} == {id_of(t) for t in ("haiku", "sonnet", "opus")}
    assert upstream.bodies[0]["model"] == id_of("sonnet")
    _post(handle.port, _turn("again", session="z"))
    assert len(upstream.gets) == 1  # a failed fetch is not retried on every turn


def test_manual_model_does_not_trigger_catalog_fetch_or_jev(world):
    route = Route()
    upstream, handle = world(route)
    _post(handle.port, _turn("x", model="claude-opus-5-5"))
    assert upstream.gets == [] and route.calls == []
    assert upstream.bodies[0]["model"] == "claude-opus-5-5"


def test_jev_is_offered_the_newest_model_per_tier_cheapest_first():
    from jev_router_live.proxy import claude_models

    catalog = [  # /v1/models order: newest first
        {"id": "claude-opus-5-5"}, {"id": "claude-sonnet-5"}, {"id": "claude-opus-5"},
        {"id": "claude-haiku-4-5-20251001"}, {"id": "claude-sonnet-4-6"}, {"id": "claude-opus-4-8"},
        {"id": "claude-3-unknown-family"},
    ]
    assert [m["id"] for m in claude_models(catalog)] == [
        "claude-haiku-4-5-20251001", "claude-sonnet-5", "claude-opus-5-5",
    ]


def test_auxiliary_sentinel_request_uses_a_catalog_model(world):
    """A sentinel request that is not a fresh turn and belongs to no routed conversation (an
    auxiliary call) runs on the fallback tier's catalog model, not a static guess."""
    route = Route()
    upstream, handle = world(route)
    _post(handle.port, _turn("prime the catalog", session="a"))

    aux = {"model": AUTO_MODEL, "messages": [{"role": "user", "content": "summarise"}]}  # no tools
    _post(handle.port, aux)

    assert len(route.calls) == 1  # aux call did not ask JEV
    assert upstream.bodies[-1]["model"] == "claude-opus-5-5"


def _reminded(text, *reminders, trailing_system=False):
    """A user message shaped like Claude Code 2.1.282's: <system-reminder> blocks, then text."""
    blocks = [{"type": "text", "text": f"<system-reminder>\n{r}\n</system-reminder>"} for r in reminders]
    msgs = [{"role": "user", "content": [*blocks, {"type": "text", "text": text}]}]
    if trailing_system:
        msgs.append({"role": "system", "content": "context"})
    return {
        "model": AUTO_MODEL,
        "tools": [{"name": "Bash", "input_schema": {}}],
        "metadata": {"user_id": json.dumps({"session_id": "cc"})},
        "messages": msgs,
    }


def test_resent_turn_with_different_reminders_asks_jev_once(world):
    """Claude Code 2.1.282 sends a turn's first request twice: once with a short set of
    reminders plus a trailing system message, then with the full set. Same turn, one JEV call,
    one conversation."""
    route = Route(choice="claude-haiku-4-5-20251001")
    upstream, handle = world(route)

    _post(handle.port, _reminded("rename x", "attribution", trailing_system=True))
    route.choice = "claude-opus-5-5"  # a second call would change the model; it must not happen
    _post(handle.port, _reminded("rename x", "environment", "skills", "attribution"))

    assert len(route.calls) == 1
    assert [b["model"] for b in upstream.bodies] == ["claude-haiku-4-5-20251001"] * 2


def test_same_prompt_on_a_later_turn_is_routed_again(world):
    route = Route(choice="claude-haiku-4-5-20251001")
    upstream, handle = world(route)
    _post(handle.port, _turn("yes"))

    later = _turn("yes")
    later["messages"] += [{"role": "assistant", "content": "ok?"}, {"role": "user", "content": "yes"}]
    route.choice = "claude-sonnet-5"
    _post(handle.port, later)

    assert len(route.calls) == 2
    assert upstream.bodies[-1]["model"] == "claude-sonnet-5"


def test_auxiliary_call_uses_its_sessions_routed_model(world):
    route = Route(choice="claude-haiku-4-5-20251001")
    upstream, handle = world(route)
    _post(handle.port, _turn("rename x", session="s9"))

    aux = {
        "model": AUTO_MODEL,
        "metadata": {"user_id": json.dumps({"session_id": "s9"})},
        "thinking": {"type": "adaptive"},
        "messages": [{"role": "user", "content": "Current state: working"}],
    }
    _post(handle.port, aux)

    assert len(route.calls) == 1
    assert upstream.bodies[-1]["model"] == "claude-haiku-4-5-20251001"
    assert "thinking" not in upstream.bodies[-1]  # stripped for the tier it actually runs on


# --- streaming ------------------------------------------------------------------------------


def test_sse_stream_is_relayed_incrementally(world):
    """The first event must reach the client while upstream is still streaming. A proxy that
    buffered the whole response would deadlock here and fail the timeout."""
    release = threading.Event()

    def streaming(h):
        h.send_response(200)
        h.send_header("Content-Type", "text/event-stream")
        h.send_header("Transfer-Encoding", "chunked")
        h.end_headers()
        first = b"event: message_start\ndata: {}\n\n"
        h.wfile.write(b"%x\r\n%s\r\n" % (len(first), first))
        h.wfile.flush()
        release.wait(5)
        last = b"event: message_stop\ndata: {}\n\n"
        h.wfile.write(b"%x\r\n%s\r\n0\r\n\r\n" % (len(last), last))

    _, handle = world(Route(), on_post=streaming)
    conn = http.client.HTTPConnection("127.0.0.1", handle.port, timeout=3)
    conn.request("POST", "/v1/messages", body=json.dumps(_turn("x")), headers={"Content-Type": "application/json"})
    resp = conn.getresponse()
    assert resp.getheader("Content-Type") == "text/event-stream"
    assert b"message_start" in resp.read1(65536)  # arrives before upstream finishes
    release.set()
    assert b"message_stop" in resp.read()
    conn.close()


def test_fixed_length_response_keeps_exact_length(world):
    upstream, handle = world(Route())
    resp, data = _post(handle.port, _turn("x"))
    assert resp.status == 200
    assert resp.getheader("Content-Length") == str(len(data))
    assert json.loads(data)["type"] == "message"


def test_upstream_status_and_error_body_pass_through(world):
    def overloaded(h):
        data = b'{"type":"error","error":{"type":"overloaded_error"}}'
        h.send_response(529)
        h.send_header("Content-Type", "application/json")
        h.send_header("Content-Length", str(len(data)))
        h.end_headers()
        h.wfile.write(data)

    _, handle = world(Route(), on_post=overloaded)
    resp, data = _post(handle.port, _turn("x"))
    assert resp.status == 529
    assert b"overloaded_error" in data


# --- connection failures --------------------------------------------------------------------


def test_upstream_reset_mid_stream_is_logged_visibly(world, monkeypatch):
    """An upstream failure is a real problem and must not be mistaken for the client
    disconnecting (which is the only reset that is silenced)."""
    logged: list[str] = []
    monkeypatch.setattr(proxy_mod, "log", logged.append)

    def reset_mid_stream(h):
        h.send_response(200)
        h.send_header("Content-Type", "text/event-stream")
        h.send_header("Transfer-Encoding", "chunked")
        h.end_headers()
        h.wfile.write(b"5\r\nhello\r\n")
        h.wfile.flush()
        # socket.close() would not release the fd while rfile/wfile hold it; close the fd
        # itself with SO_LINGER=0 so the kernel sends a real RST, like a dropped connection.
        h.connection.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack("ii", 1, 0))
        os.close(h.connection.detach())
        h.close_connection = True

    _, handle = world(Route(), on_post=reset_mid_stream)
    conn = http.client.HTTPConnection("127.0.0.1", handle.port, timeout=3)
    conn.request("POST", "/v1/messages", body=json.dumps(_turn("x")), headers={"Content-Type": "application/json"})
    resp = conn.getresponse()
    with pytest.raises((http.client.IncompleteRead, ConnectionError)):
        resp.read()  # the client sees a truncated stream, not a fake clean end
    conn.close()
    time.sleep(0.2)
    assert any("upstream connection failed mid-response" in line for line in logged)


def test_unreachable_upstream_returns_502_and_logs(monkeypatch):
    logged: list[str] = []
    monkeypatch.setattr(proxy_mod, "log", logged.append)
    handle = start_proxy(upstream_url="http://127.0.0.1:9", route=Route())
    try:
        resp, data = _post(handle.port, _turn("x", model="claude-sonnet-5"))
    finally:
        handle.close()
    assert resp.status == 502
    assert json.loads(data)["type"] == "error"
    assert any("upstream request failed" in line for line in logged)


def test_client_disconnect_is_quiet_but_other_errors_are_logged(monkeypatch):
    logged: list[str] = []
    monkeypatch.setattr(proxy_mod, "log", logged.append)
    server = proxy_mod._ProxyServer.__new__(proxy_mod._ProxyServer)
    for exc in (ConnectionResetError(10054, "reset"), ConnectionAbortedError(10053, "aborted"), BrokenPipeError()):
        try:
            raise exc
        except OSError:
            server.handle_error(None, ("127.0.0.1", 1))
    assert logged == []
    try:
        raise ValueError("real bug")
    except ValueError:
        server.handle_error(None, ("127.0.0.1", 1))
    assert len(logged) == 1 and "ValueError" in logged[0]


# --- observability / security ---------------------------------------------------------------


def test_decision_log_has_safe_metadata_only(world, monkeypatch):
    recorded: list[str] = []
    monkeypatch.setattr(proxy_mod, "record", recorded.append)
    monkeypatch.setenv("JEV_API_KEY", "secret-key-value")
    _, handle = world(Route(choice="claude-sonnet-5", confidence=0.99))

    _post(handle.port, _turn("my private prompt text"), headers={"Authorization": "Bearer oauth-secret"})

    line = next(line for line in recorded if "decision=" in line)
    assert "decision=sonnet" in line and "model=claude-sonnet-5" in line
    assert "confidence=0.99" in line and "latency=7ms" in line and "reason=jev" in line
    joined = "\n".join(recorded)
    for secret in ("my private prompt text", "secret-key-value", "oauth-secret"):
        assert secret not in joined


posix_only = pytest.mark.skipif(not hasattr(os, "getuid"), reason="POSIX ownership semantics")


@posix_only
def test_status_files_are_owner_only_from_creation():
    from jev_router_live import status

    status.write_status("sess", {"tier": "haiku", "prompt": "secret"})
    path = status._file_for("sess")
    assert (path.stat().st_mode & 0o777) == 0o600
    assert (status.STATUS_DIR.stat().st_mode & 0o777) == 0o700


@posix_only
def test_status_dir_owned_by_someone_else_is_never_used(monkeypatch):
    from jev_router_live import status

    status.STATUS_DIR.mkdir(mode=0o755)
    monkeypatch.setattr(os, "getuid", lambda: os.stat(status.STATUS_DIR).st_uid + 1)
    status.write_status("sess", {"prompt": "secret"})
    assert not status._file_for("sess").exists()
    assert status.read_status("sess") is None


@posix_only
def test_symlinked_status_dir_is_refused(tmp_path):
    from jev_router_live import status

    elsewhere = tmp_path / "attacker"
    elsewhere.mkdir()
    status.STATUS_DIR.symlink_to(elsewhere)
    status.write_status("sess", {"prompt": "secret"})
    assert list(elsewhere.iterdir()) == []


@posix_only
def test_statusline_settings_file_is_private_unique_and_cleaned_up(launched, monkeypatch):
    from jev_router_live.bin import jev_claude

    monkeypatch.delenv("JEV_NO_STATUSLINE")
    monkeypatch.setattr(jev_claude.Path, "cwd", lambda: jev_claude.Path("/nonexistent"))
    monkeypatch.setattr(jev_claude.Path, "home", lambda: jev_claude.Path("/nonexistent"))
    monkeypatch.setenv("JEV_API_KEY", "k")
    captured = {}
    real_run = jev_claude.subprocess.run

    def run_and_inspect(argv, env):
        settings = jev_claude.Path(argv[argv.index("--settings") + 1])
        captured["path"] = settings
        captured["mode"] = settings.stat().st_mode & 0o777
        captured["content"] = json.loads(settings.read_text())
        return real_run(argv, env)

    monkeypatch.setattr(jev_claude.subprocess, "run", run_and_inspect)
    launched()

    assert captured["mode"] == 0o600
    assert captured["path"].name != "settings.json"  # unique, not a guessable shared name
    assert "jev_statusline" in captured["content"]["statusLine"]["command"]
    assert not captured["path"].exists()  # removed when the session ends


@pytest.mark.parametrize("status,expected_calls", [(401, 1), (400, 1), (503, 2)])
def test_jev_client_retries_only_retryable_failures(monkeypatch, status, expected_calls):
    import urllib.error

    from jev_router_live import stdlib_router

    calls = []

    def fail(*a):
        calls.append(1)
        raise urllib.error.HTTPError("u", status, "err", {}, None)

    monkeypatch.setenv("JEV_API_KEY", "k")
    monkeypatch.setattr(stdlib_router, "_post", fail)
    models = [{"id": "claude-sonnet-5", "tier": "sonnet"}]
    assert stdlib_router.stdlib_ask_jev(prompt="x", current="c", context_tokens=0, models=models) is None
    assert len(calls) == expected_calls


# --- conversation isolation -----------------------------------------------------------------


def test_sessions_and_subagents_pin_independently(world):
    route = Route(choice="claude-haiku-4-5-20251001")
    upstream, handle = world(route)
    _post(handle.port, _turn("main task", session="s1"))

    route.choice = "claude-opus-5-5"
    _post(handle.port, _turn("sub-agent task", session="s1", first="You are a sub-agent"))
    _post(handle.port, _turn("other session", session="s2"))

    # A tool continuation of the main conversation keeps the main conversation's model.
    cont = _turn("main task", session="s1")
    cont["messages"] += [
        {"role": "assistant", "content": [{"type": "tool_use", "id": "t", "name": "Bash", "input": {}}]},
        {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "t", "content": "ok"}]},
    ]
    _post(handle.port, cont)

    assert len(route.calls) == 3
    assert [b["model"] for b in upstream.bodies] == [
        "claude-haiku-4-5-20251001",
        "claude-opus-5-5",
        "claude-opus-5-5",
        "claude-haiku-4-5-20251001",
    ]


def test_sentinel_never_reaches_upstream_even_when_routing_crashes(world):
    def crash(**kw):
        raise RuntimeError("boom")

    upstream, handle = world(crash)
    resp, _ = _post(handle.port, _turn("x"))
    assert resp.status == 200
    assert upstream.bodies[0]["model"] != AUTO_MODEL


# --- launcher -------------------------------------------------------------------------------


@pytest.fixture
def launched(monkeypatch, tmp_path):
    from jev_router_live.bin import jev_claude

    seen: dict = {}

    class Done:
        returncode = 0

    def fake_run(argv, env):
        seen["argv"], seen["env"] = argv, env
        return Done()

    monkeypatch.setattr(jev_claude, "_resolve_claude", lambda: "/usr/bin/claude")
    monkeypatch.setattr(jev_claude, "load_env", lambda: None)
    monkeypatch.setattr(jev_claude.subprocess, "run", fake_run)
    monkeypatch.setattr(jev_claude, "read_saved_model", lambda: None)
    monkeypatch.setattr(jev_claude, "restore_saved_model", lambda prev: None)
    monkeypatch.setenv("JEV_NO_STATUSLINE", "1")
    monkeypatch.delenv("ANTHROPIC_MODEL", raising=False)
    monkeypatch.setattr(jev_claude.sys, "argv", ["jev-claude", "-p", "hi"])

    def run():
        with pytest.raises(SystemExit) as exit_info:
            jev_claude.main()
        seen["code"] = exit_info.value.code
        return seen

    return run


def test_launcher_with_key_starts_proxy_and_picker(launched, monkeypatch):
    monkeypatch.setenv("JEV_API_KEY", "k")
    seen = launched()
    env = seen["env"]
    assert env["ANTHROPIC_BASE_URL"].startswith("http://127.0.0.1:")
    assert env["ANTHROPIC_CUSTOM_MODEL_OPTION"] == AUTO_MODEL
    assert env["ANTHROPIC_CUSTOM_MODEL_OPTION_NAME"] == "JEV Router"
    assert env["ANTHROPIC_MODEL"] == AUTO_MODEL
    assert seen["argv"] == ["/usr/bin/claude", "-p", "hi"]  # user args untouched, no --add-dir
    assert seen["code"] == 0


def test_launcher_without_jev_api_key_runs_plain_claude(launched, monkeypatch):
    monkeypatch.delenv("JEV_API_KEY", raising=False)
    monkeypatch.setenv("TYPESAFE_API_KEY", "legacy")  # must not enable routing
    monkeypatch.setenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com")
    env = launched()["env"]
    assert env["ANTHROPIC_BASE_URL"] == "https://api.anthropic.com"
    assert "ANTHROPIC_CUSTOM_MODEL_OPTION" not in env
    assert env.get("ANTHROPIC_MODEL") != AUTO_MODEL


def test_launcher_respects_users_own_model_choice(launched, monkeypatch):
    monkeypatch.setenv("JEV_API_KEY", "k")
    monkeypatch.setenv("ANTHROPIC_MODEL", "claude-opus-5-5")
    assert launched()["env"]["ANTHROPIC_MODEL"] == "claude-opus-5-5"
