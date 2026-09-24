"""Port of jev-router's ``src/proxy.mjs``: the Claude Code per-turn routing proxy.

A local HTTP server sits between Claude Code and ``api.anthropic.com``. Claude Code is told
to use it as ``ANTHROPIC_BASE_URL`` and to offer a sentinel "Jev Router" row in `/model`
(see ``bin/jev_claude.py``). Every request whose ``model`` is that sentinel gets a fresh
routing decision (for a genuinely new user turn) or the tier already chosen for this
conversation (for a tool-call continuation) rewritten into the body before it is forwarded
upstream.
"""
from __future__ import annotations

import http.client
import json
import os
import re
import socket
import ssl
import threading
from hashlib import sha1
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Callable
from urllib.parse import urlparse

from jev_router_live.config import (
    TIERS,
    available_tiers,
    id_of,
    is_auto,
    rank_of,
    should_use_exact_model,
    tier_of,
    tier_spec,
)
from jev_router_live.log import debug
from jev_router_live.policy import decide
from jev_router_live.router import ask_jev
from jev_router_live.status import write_decision, write_status

ANTHROPIC_BASE_URL = "https://api.anthropic.com"

_SYSTEM_REMINDER_RE = re.compile(r"<system-reminder>.*?</system-reminder>", re.S)


def sanitize_schema(node: Any) -> None:
    """Claude Code converts draft-04 relics in MCP tool schemas before sending them
    first-party, but skips that when ANTHROPIC_BASE_URL is set, so the API rejects the
    request. In draft 2020-12 ``exclusiveMinimum``/``exclusiveMaximum`` are numbers, not
    booleans."""
    if isinstance(node, list):
        for item in node:
            sanitize_schema(item)
        return
    if not isinstance(node, dict):
        return
    for key, bound in (("exclusiveMinimum", "minimum"), ("exclusiveMaximum", "maximum")):
        if isinstance(node.get(key), bool):
            if node[key] and isinstance(node.get(bound), (int, float)):
                node[key] = node[bound]
                node.pop(bound, None)
            else:
                node.pop(key, None)
    for value in node.values():
        sanitize_schema(value)


def new_turn_prompt(body: dict) -> str | None:
    """The text of a genuinely new user turn, or None.

    A turn can continue for many requests while Claude works through tool calls, and those
    continuations end in a ``tool_result`` rather than typed text. Routing them would re-ask
    Jev on every tool call and let the model flip mid-task, so only the opening request of a
    turn counts. Claude Code also injects ``<system-reminder>`` blocks into the user message,
    which are noise to a router and measurably blunt Jev's confidence, so they are removed.
    """
    tools = body.get("tools")
    if not isinstance(tools, list) or not tools:
        return None  # auxiliary call
    messages = body.get("messages") or []
    last = messages[-1] if messages else None
    if not last or last.get("role") != "user":
        return None
    content = last.get("content")
    if isinstance(content, str):
        text = content
    elif isinstance(content, list):
        if any(b.get("type") == "tool_result" for b in content):
            return None
        text = "\n".join(b.get("text", "") for b in content if b.get("type") == "text")
    else:
        return None
    return _SYSTEM_REMINDER_RE.sub("", text).strip() or None


def apply_tier(body: dict, tier_name: str, model: str | None = None) -> dict:
    """Points a request at a tier, removing request fields that tier cannot accept. Claude
    Code composes the body for whatever model it thinks it is talking to, so downgrading to
    Haiku while leaving ``thinking: {type: "adaptive"}`` in place is a hard 400."""
    tier = tier_spec(tier_name)
    if not tier:
        return body
    body["model"] = model or id_of(tier_name)
    if not tier.thinking:
        body.pop("thinking", None)
        # A context-management strategy that prunes thinking blocks is itself rejected once
        # thinking is gone, so it has to go with it.
        edits = (body.get("context_management") or {}).get("edits")
        if isinstance(edits, list):
            body["context_management"]["edits"] = [
                e for e in edits if not re.search("thinking", str(e.get("type", "")), re.I)
            ]
            if not body["context_management"]["edits"]:
                body.pop("context_management", None)
    if not tier.effort and isinstance(body.get("output_config"), dict):
        body["output_config"].pop("effort", None)
        if not body["output_config"]:
            body.pop("output_config", None)
    return body


def claude_models(catalog: list[dict] | None = None) -> list[dict]:
    """Exact Claude models reported by the account, newest first; static ids are the
    cold-start fallback."""
    models = []
    for model in catalog or []:
        tier = tier_of(model.get("id"))
        if not tier:
            continue
        parts = [
            model.get("display_name"),
            model.get("created_at") and f"released {model['created_at'][:10]}",
            model.get("max_input_tokens") and f"{model['max_input_tokens']} input tokens",
        ]
        models.append({"id": model["id"], "tier": tier, "description": "; ".join(p for p in parts if p)})
    if models:
        return models
    return [{"id": t.id, "tier": t.name, "description": t.id} for t in TIERS]


def _model_for_tier(models: list[dict], tier: str) -> str | None:
    return next((m["id"] for m in models if m["tier"] == tier), id_of(tier))


def session_of(body: dict) -> str:
    """Session id Claude Code embeds in request metadata, or "" when absent.
    ``metadata.user_id`` is a JSON string, not a plain id."""
    try:
        raw = (body.get("metadata") or {}).get("user_id") or "{}"
        return json.loads(raw).get("session_id") or ""
    except (ValueError, AttributeError):
        return ""


def conversation_key(body: dict) -> str:
    """Identifies the conversation a request belongs to. Claude Code runs sub-agents through
    the same endpoint, so a single pinned model would let a sub-agent's choice leak into the
    main conversation.

    Only stable fields may be used: the session id plus the text of the first message, which
    is fixed once a conversation starts and differs between the main agent and each
    sub-agent."""
    session = session_of(body)
    messages = body.get("messages") or []
    content = messages[0].get("content") if messages else None
    if isinstance(content, str):
        text = content
    elif isinstance(content, list):
        text = "".join(b.get("text", "") for b in content if b.get("type") == "text")
    else:
        text = ""
    return sha1(f"{session}|{text}".encode()).hexdigest()[:12]


class _ConvoState:
    __slots__ = ("tier", "model")

    def __init__(self) -> None:
        self.tier: str | None = None
        self.model: str | None = None


class _Convos:
    """Bounded LRU-ish map of conversation key -> routing state, mirroring proxy.mjs's cap."""

    def __init__(self, limit: int = 50) -> None:
        self._data: dict[str, _ConvoState] = {}
        self._limit = limit
        self._lock = threading.Lock()

    def get(self, key: str) -> _ConvoState:
        with self._lock:
            state = self._data.get(key)
            if state is None:
                if len(self._data) > self._limit:
                    self._data.pop(next(iter(self._data)))
                state = self._data[key] = _ConvoState()
            return state


def _forward_headers(headers: dict, target_host: str) -> dict:
    out = {k: v for k, v in headers.items() if k.lower() != "content-length"}
    out["Host"] = target_host
    return out


def _make_handler(
    upstream_url: str, route: Callable[..., dict | None], convos: _Convos, catalog: dict[str, dict]
) -> type[BaseHTTPRequestHandler]:
    target = urlparse(upstream_url)

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, fmt: str, *args: Any) -> None:  # noqa: A002 - stdlib signature
            pass  # Silence BaseHTTPRequestHandler's own stderr access log.

        def do_HEAD(self) -> None:  # Claude Code probes the base URL before its first request.
            self.send_response(200)
            self.end_headers()

        def do_GET(self) -> None:
            self._proxy(b"")

        def do_POST(self) -> None:
            length = int(self.headers.get("Content-Length", 0) or 0)
            body = self.rfile.read(length) if length else b""
            self._proxy(body)

        def _rewrite(self, raw: bytes) -> bytes:
            if not re.match(r"^/v1/messages", self.path):
                return raw
            try:
                body = json.loads(raw.decode("utf-8"))
            except ValueError:
                return raw
            try:
                for tool in body.get("tools") or []:
                    sanitize_schema(tool.get("input_schema"))

                if not is_auto(body.get("model")):
                    debug(f"passthrough, user selected {body.get('model')}")
                    if isinstance(body.get("tools"), list):
                        write_status(session_of(body), {"manual": True, "at": _now_ms()})
                    return raw

                key = conversation_key(body)
                state = convos.get(key)
                current = state.tier or "opus"
                prompt = new_turn_prompt(body)
                explaining = bool(prompt and "<jev-explain>" in prompt)
                fresh: dict | None = None

                if prompt and not explaining:
                    models = [m for m in claude_models(list(catalog.values())) if m["tier"] in available_tiers()]
                    available = sorted({m["tier"] for m in models}, key=rank_of)
                    current_model = state.model or _model_for_tier(models, current)
                    context_tokens = round(len(json.dumps(body.get("messages"))) / 4)
                    jev = route(prompt=prompt, current=current_model, context_tokens=context_tokens, models=models)
                    chosen = next((m for m in models if m["id"] == (jev or {}).get("choice")), None)
                    tier_answer = {**jev, "choice": chosen["tier"] if chosen else None} if jev else None
                    decision = decide(
                        prompt=prompt,
                        jev=tier_answer,
                        current=current,
                        available=available,
                        context_tokens=context_tokens,
                    )
                    tier, reason = decision["tier"], decision["reason"]
                    if should_use_exact_model(reason, chosen["tier"] if chosen else None, tier):
                        model = chosen["id"]
                    elif tier == current:
                        model = current_model
                    else:
                        model = _model_for_tier(models, tier)
                    state.tier, state.model = tier, model
                    fresh = {
                        "prompt": prompt,
                        "model": model,
                        "confidence": (jev or {}).get("confidence"),
                        "metrics": (jev or {}).get("metrics"),
                        "reason": reason,
                        "jev": {"request": jev["request"], "response": jev["response"]} if jev else None,
                    }
                    jev_desc = f"{jev['ms']}ms p={jev['confidence']:.2f}" if jev else "no-jev"
                    debug(
                        f"{key} {jev_desc} {current} -> {tier} ({reason}) "
                        f"ctx~{context_tokens} | {prompt[:60]}"
                    )

                tier = state.tier or current
                model = state.model or id_of(tier)
                debug(f"{key} rewrite {body.get('model')} -> {model}")
                apply_tier(body, tier, model)
                if fresh and not explaining:
                    write_decision(session_of(body) or key, {"tier": tier, **fresh, "at": _now_ms()})
                return json.dumps(body).encode("utf-8")
            except Exception as exc:  # noqa: BLE001
                debug(f"passthrough, could not process body: {exc}")
                return raw

        def _proxy(self, body: bytes) -> None:
            out = self._rewrite(body) if self.command == "POST" else body
            headers = _forward_headers(dict(self.headers), target.netloc)
            is_models = self.command == "GET" and re.match(r"^/v1/models(?:\?|$)", self.path)
            if is_models:
                headers.pop("Accept-Encoding", None)
                headers.pop("accept-encoding", None)
            if os.environ.get("JEV_DEBUG"):
                headers.pop("Accept-Encoding", None)
                headers.pop("accept-encoding", None)

            try:
                if target.scheme == "https":
                    conn = http.client.HTTPSConnection(target.hostname, target.port or 443, context=ssl.create_default_context())
                else:
                    conn = http.client.HTTPConnection(target.hostname, target.port or 80)
                path = f"{target.path.rstrip('/')}{self.path}"
                conn.request(self.command, path, body=out if out else None, headers=headers)
                upstream = conn.getresponse()
            except (OSError, socket.error, http.client.HTTPException) as exc:
                debug(f"upstream error: {exc}")
                payload = json.dumps({"type": "error", "error": {"message": str(exc)}}).encode()
                self.send_response(502)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)
                return

            data = upstream.read()
            if is_models:
                try:
                    for model in json.loads(data.decode("utf-8")).get("data", []):
                        if tier_of(model.get("id")):
                            catalog[model["id"]] = model
                except ValueError as exc:
                    debug(f"could not read Claude model catalog: {exc}")

            resp_headers = {k: v for k, v in upstream.getheaders() if k.lower() != "content-length"}
            self.send_response(upstream.status)
            for k, v in resp_headers.items():
                self.send_header(k, v)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            conn.close()

    return Handler


def _now_ms() -> int:
    import time

    return int(time.time() * 1000)


class ProxyHandle:
    def __init__(self, server: ThreadingHTTPServer, thread: threading.Thread) -> None:
        self._server = server
        self._thread = thread
        self.port = server.server_address[1]

    def close(self) -> None:
        self._server.shutdown()
        self._server.server_close()
        self._thread.join(timeout=2)


def start_proxy(upstream_url: str = ANTHROPIC_BASE_URL, route: Callable[..., dict | None] = ask_jev) -> ProxyHandle:
    convos = _Convos()
    catalog: dict[str, dict] = {}
    handler_cls = _make_handler(upstream_url, route, convos, catalog)
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler_cls)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return ProxyHandle(server, thread)
