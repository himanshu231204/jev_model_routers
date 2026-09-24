"""The OpenAI Codex per-turn routing proxy."""
from __future__ import annotations

import http.client
import json
import os
import re
import socket
import ssl
import threading
import uuid
from hashlib import sha1
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Callable
from urllib.parse import urlparse

from jev_router_live.config import available_tiers, should_use_exact_model
from jev_router_live.log import debug
from jev_router_live.policy import decide
from jev_router_live.proxy import ProxyHandle
from jev_router_live.router import ask_jev
from jev_router_live.status import write_decision, write_status

CHATGPT_BASE_URL = "https://chatgpt.com/backend-api/codex"
API_BASE_URL = "https://api.openai.com/v1"
CODEX_AUTO_MODEL = "jev-router"

_DEFAULT_MODELS = {
    "haiku": "gpt-5.6-luna",
    "sonnet": "gpt-5.6-terra",
    "opus": "gpt-5.6-sol",
    "fable": "gpt-6-astra",
}
_MODEL_ENV = {
    "haiku": "JEV_CODEX_FAST_MODEL",
    "sonnet": "JEV_CODEX_BALANCED_MODEL",
    "opus": "JEV_CODEX_STRONG_MODEL",
    "fable": "JEV_CODEX_LONG_MODEL",
}


def codex_model_of(tier: str) -> str:
    return os.environ.get(_MODEL_ENV[tier], _DEFAULT_MODELS[tier])


def codex_tier_of(model: str | None) -> str | None:
    for tier in _DEFAULT_MODELS:
        if codex_model_of(tier) == model:
            return tier
    text = model or ""
    if re.search(r"(?:astra|fable|long)", text, re.I):
        return "fable"
    if re.search(r"(?:sol|opus|strong|max|pro)", text, re.I):
        return "opus"
    if re.search(r"(?:luna|haiku|fast|mini|nano)", text, re.I):
        return "haiku"
    return "sonnet" if re.match(r"^gpt-", text, re.I) else None


def codex_models(models: dict[str, dict]) -> list[dict]:
    """Exact GPT models in Codex's account catalog; configured ids are the cold-start fallback."""
    available = []
    for model in models.values():
        if model.get("slug") == CODEX_AUTO_MODEL or model.get("supported_in_api") is False:
            continue
        tier = codex_tier_of(model.get("slug"))
        if not tier:
            continue
        parts = [
            model.get("display_name"),
            model.get("description"),
            model.get("context_window") and f"{model['context_window']} context tokens",
        ]
        available.append({"id": model["slug"], "tier": tier, "description": "; ".join(p for p in parts if p)})
    if available:
        return available
    return [{"id": codex_model_of(t), "tier": t, "description": codex_model_of(t)} for t in _DEFAULT_MODELS]


def _model_for_tier(models: list[dict], tier: str) -> str:
    return next((m["id"] for m in models if m["tier"] == tier), codex_model_of(tier))


def _text_of(content: Any) -> str:
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return ""
    return "\n".join(i.get("text", "") for i in content if i.get("type") in ("text", "input_text"))


_STRIP_TAGS = re.compile(
    r"<system[-_]reminder>.*?</system[-_]reminder>|<current_datetime>.*?</current_datetime>"
    r"|<environment_context>.*?</environment_context>",
    re.S | re.I,
)


def _clean_prompt(text: str) -> str:
    return _STRIP_TAGS.sub("", text).strip()


def is_codex_auxiliary_prompt(prompt: str) -> bool:
    return bool(re.match(r"^Generate a concise, single-line task title\b", prompt, re.I))


def codex_new_turn_prompt(body: dict) -> str | None:
    items = body.get("input")
    if not isinstance(items, list) or not any(i.get("type") == "additional_tools" for i in items):
        return None
    for item in reversed(items):
        if item.get("type") in ("function_call_output", "custom_tool_call_output"):
            return None
        if item.get("role") != "user":
            continue
        prompt = _clean_prompt(_text_of(item.get("content")))
        if prompt and not is_codex_auxiliary_prompt(prompt):
            return prompt
    return None


def codex_conversation_key(body: dict) -> str:
    stable = body.get("prompt_cache_key") or (body.get("client_metadata") or {}).get("x-codex-turn-metadata")
    if not stable:
        first_user = next((i for i in body.get("input") or [] if i.get("role") == "user"), None)
        stable = f"{body.get('instructions', '')}|{_text_of((first_user or {}).get('content'))}"
    return sha1(str(stable).encode()).hexdigest()[:12]


def add_jev_model(catalog: dict) -> dict:
    models = catalog.get("models")
    if not isinstance(models, list) or any(m.get("slug") == CODEX_AUTO_MODEL for m in models):
        return catalog
    template = next((m for m in models if m.get("slug") == codex_model_of("sonnet")), None)
    template = template or next((m for m in models if m.get("visibility") == "list"), None)
    template = template or (models[0] if models else None)
    if not template:
        return catalog
    models.insert(
        0,
        {
            **template,
            "slug": CODEX_AUTO_MODEL,
            "display_name": "Jev Router",
            "description": "Jev picks the cheapest model that can complete each turn.",
            "visibility": "list",
            "supported_in_api": True,
            "priority": 0,
            "upgrade": None,
        },
    )
    return catalog


def apply_codex_tier(body: dict, tier: str, models: dict[str, dict], model: str | None = None) -> dict:
    model = model or codex_model_of(tier)
    body["model"] = model
    info = models.get(model) or {}
    efforts = [level.get("effort") for level in info.get("supported_reasoning_levels") or []]
    reasoning = body.get("reasoning") or {}
    if reasoning.get("effort") and efforts and reasoning["effort"] not in efforts:
        reasoning["effort"] = info.get("default_reasoning_level")
    return body


def upstream_for(headers: dict, path: str = "", chatgpt_base_url: str = CHATGPT_BASE_URL, api_base_url: str = API_BASE_URL) -> str:
    is_models_path = bool(re.search(r"/models(?:\?|$)", path or ""))
    has_account_header = any(k.lower() == "chatgpt-account-id" for k in headers)
    return chatgpt_base_url if (is_models_path or has_account_header) else api_base_url


def jev_decision_events(tier: str, model: str | None, confidence: float | None, reason: str) -> bytes:
    model = model or codex_model_of(tier)
    detail = reason if confidence is None else f"{reason}, confidence {confidence:.2f}"
    event_id = f"jev-{uuid.uuid4()}"
    if reason.startswith("jev-unavailable"):
        text = f"[Jev] unavailable; using {model}. Add JEV_API_KEY=... to ~/.jev-router.env and restart jev-codex."
    else:
        text = f"[Jev] routed this turn to {model} ({detail})."
    item = {"type": "message", "role": "assistant", "id": event_id, "phase": "commentary", "content": [{"type": "output_text", "text": text}]}
    events = [
        {"type": "response.output_item.added", "item": {**item, "content": []}},
        {"type": "response.output_text.delta", "item_id": event_id, "delta": text},
        {"type": "response.output_item.done", "item": item},
    ]
    return "".join(f"event: {e['type']}\ndata: {json.dumps(e)}\n\n" for e in events).encode("utf-8")


def _now_ms() -> int:
    import time

    return int(time.time() * 1000)


def _make_handler(
    chatgpt_base_url: str, api_base_url: str, route: Callable[..., dict | None], status_id: str,
    states: dict[str, dict], models: dict[str, dict],
) -> type[BaseHTTPRequestHandler]:
    lock = threading.Lock()

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, fmt: str, *args: Any) -> None:
            pass

        def do_GET(self) -> None:
            self._proxy(b"")

        def do_POST(self) -> None:
            length = int(self.headers.get("Content-Length", 0) or 0)
            body = self.rfile.read(length) if length else b""
            self._proxy(body)

        def _rewrite(self, raw: bytes) -> tuple[bytes, dict | None]:
            if not (self.command == "POST" and re.search(r"/responses(?:\?|$)", self.path)):
                return raw, None
            try:
                body = json.loads(raw.decode("utf-8"))
            except ValueError:
                return raw, None
            routing: dict | None = None
            try:
                if body.get("model") == CODEX_AUTO_MODEL:
                    key = codex_conversation_key(body)
                    candidates = [m for m in codex_models(models) if m["tier"] in available_tiers()]
                    available = list({m["tier"] for m in candidates})
                    with lock:
                        prev = states.get(key)
                    current_model = (prev or {}).get("model") or _model_for_tier(candidates, "opus")
                    current = codex_tier_of(current_model) or "opus"
                    prompt = codex_new_turn_prompt(body)
                    explaining = bool(prompt) and (
                        "<jev-explain>" in (prompt or "") or bool(re.match(r"^\$jev-explain\b", prompt or "", re.I))
                    )
                    tier, model = current, current_model
                    if prompt and not explaining:
                        context_tokens = round(len(json.dumps(body.get("input"))) / 4)
                        jev = route(prompt=prompt, current=current_model, context_tokens=context_tokens, models=candidates)
                        chosen = next((c for c in candidates if c["id"] == (jev or {}).get("choice")), None)
                        tier_answer = {**jev, "choice": chosen["tier"] if chosen else None} if jev else None
                        decision = decide(prompt=prompt, jev=tier_answer, current=current, available=available, context_tokens=context_tokens)
                        tier, reason = decision["tier"], decision["reason"]
                        if should_use_exact_model(reason, chosen["tier"] if chosen else None, tier):
                            model = chosen["id"]
                        elif tier == current:
                            model = current_model
                        else:
                            model = _model_for_tier(candidates, tier)
                        with lock:
                            states[key] = {"tier": tier, "model": model}
                        routing = {
                            "prompt": prompt, "tier": tier, "model": model,
                            "confidence": (jev or {}).get("confidence"), "metrics": (jev or {}).get("metrics"),
                            "reason": reason,
                            "jev": {"request": jev["request"], "response": jev["response"]} if jev else None,
                            "at": _now_ms(),
                        }
                        write_decision(status_id, routing)
                        debug(f"{key} {current} -> {tier} ({reason}) | {prompt[:60]}")
                    apply_codex_tier(body, tier, models, model)
                else:
                    prompt = codex_new_turn_prompt(body)
                    explaining = bool(prompt) and (
                        "<jev-explain>" in (prompt or "") or bool(re.match(r"^\$jev-explain\b", prompt or "", re.I))
                    )
                    if prompt and not explaining:
                        write_status(status_id, {"manual": True, "at": _now_ms()})
                return json.dumps(body).encode("utf-8"), routing
            except Exception as exc:  # noqa: BLE001
                debug(f"codex passthrough, could not process body: {exc}")
                return raw, None

        def _proxy(self, body: bytes) -> None:
            out, routing = self._rewrite(body)
            base = upstream_for(dict(self.headers), self.path, chatgpt_base_url, api_base_url)
            target = urlparse(base)
            headers = {k: v for k, v in dict(self.headers).items() if k.lower() != "content-length"}
            headers["Host"] = target.netloc
            try:
                if target.scheme == "https":
                    conn = http.client.HTTPSConnection(target.hostname, target.port or 443, context=ssl.create_default_context())
                else:
                    conn = http.client.HTTPConnection(target.hostname, target.port or 80)
                path = f"{target.path.rstrip('/')}{self.path}"
                conn.request(self.command, path, body=out if out else None, headers=headers)
                upstream = conn.getresponse()
            except (OSError, socket.error, http.client.HTTPException) as exc:
                debug(f"codex upstream error: {exc}")
                payload = json.dumps({"error": {"message": str(exc), "type": "proxy_error"}}).encode()
                self.send_response(502)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)
                return

            is_models = self.command == "GET" and re.search(r"/models(?:\?|$)", self.path)
            data = upstream.read()
            resp_headers = {k: v for k, v in upstream.getheaders() if k.lower() != "content-length"}
            if is_models:
                try:
                    catalog = add_jev_model(json.loads(data.decode("utf-8")))
                    for model in catalog.get("models", []):
                        models[model["slug"]] = model
                    data = json.dumps(catalog).encode("utf-8")
                except ValueError as exc:
                    debug(f"could not extend Codex model catalog: {exc}")
                self.send_response(upstream.status)
                for k, v in resp_headers.items():
                    self.send_header(k, v)
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
                conn.close()
                return

            inject = bool(routing) and 200 <= upstream.status < 300
            self.send_response(upstream.status)
            for k, v in resp_headers.items():
                if inject and k.lower() == "content-length":
                    continue
                self.send_header(k, v)
            self.end_headers()
            if not inject:
                self.wfile.write(data)
                conn.close()
                return
            end = data.find(b"\n\n")
            if end < 0:
                self.wfile.write(data)
                conn.close()
                return
            first = data[: end + 2]
            self.wfile.write(first)
            if re.match(rb"^(?:event|data):", first, re.M):
                self.wfile.write(jev_decision_events(routing["tier"], routing.get("model"), routing.get("confidence"), routing["reason"]))
            self.wfile.write(data[end + 2 :])
            conn.close()

    return Handler


def start_codex_proxy(
    chatgpt_base_url: str = CHATGPT_BASE_URL, api_base_url: str = API_BASE_URL,
    route: Callable[..., dict | None] = ask_jev, status_id: str = "",
) -> ProxyHandle:
    states: dict[str, dict] = {}
    models: dict[str, dict] = {}
    handler_cls = _make_handler(chatgpt_base_url, api_base_url, route, status_id, states, models)
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler_cls)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return ProxyHandle(server, thread)
