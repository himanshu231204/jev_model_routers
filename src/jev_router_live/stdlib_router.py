"""Stdlib HTTP path for the live proxy: asks Jev which exact model fits a prompt.

Talks to the System One HTTP API directly with stdlib ``urllib`` (zero runtime
deps).
"""
from __future__ import annotations

import json
import os
import threading
import time
import urllib.error
import urllib.request
from typing import Any, Callable

from jev_router_live.config import (
    COMPLEXITY_MAX_SCORE,
    JEV_MODEL,
    CONTEXT_WINDOW_TOKENS,
    QUESTIONS,
    THRESHOLDS,
    question_for_models,
)
from jev_router_live.config import api_key as config_api_key
from jev_router_live.log import log

_ENDPOINT = os.environ.get("JEV_ENDPOINT", "https://api.typesafe.ai/v1/systemone")


def _post(payload: dict, headers: dict, timeout_s: float) -> dict:
    req = urllib.request.Request(
        _ENDPOINT, data=json.dumps(payload).encode(), headers=headers, method="POST"
    )
    with urllib.request.urlopen(req, timeout=timeout_s) as resp:
        return json.loads(resp.read().decode() or "{}")


def call_with_deadline(fn: Callable[[], Any], timeout_s: float) -> tuple[Any, Exception | None]:
    """Runs ``fn`` on a daemon thread, bounded by a real wall-clock deadline.

    Client timeouts only bound individual socket operations (connect, each read) -- a request
    whose DNS/connect/TLS/read steps are each fast but add up can run far longer than that.
    Joining a daemon thread against a wall-clock timeout makes the deadline real without
    hanging process exit if the thread is still stuck. Shared with ``sdk_router``.
    """
    result: dict[str, Any] = {}

    def target() -> None:
        try:
            result["raw"] = fn()
        except Exception as exc:  # noqa: BLE001 - reported to caller, not raised here
            result["error"] = exc

    thread = threading.Thread(target=target, daemon=True)
    thread.start()
    thread.join(timeout_s)
    if thread.is_alive():
        return None, TimeoutError("jev_wall_clock_deadline_exceeded")
    if "error" in result:
        return None, result["error"]
    return result.get("raw"), None


def _post_with_wall_clock_timeout(payload: dict, headers: dict, timeout_s: float) -> tuple[dict | None, Exception | None]:
    """Runs one HTTP attempt, bounded by a real wall-clock deadline."""
    return call_with_deadline(lambda: _post(payload, headers, timeout_s), timeout_s)


def _is_client_error(err: Exception) -> bool:
    return isinstance(err, urllib.error.HTTPError) and 400 <= err.code < 500


def stdlib_ask_jev(*, prompt: str, current: str, context_tokens: int, models: list[dict]) -> dict | None:
    """Asks Jev which exact model fits this prompt. Returns None on any failure, which the
    policy layer reads as "keep the current model" -- routing must never block a prompt.

    Returns {"choice": str, "confidence": float, "probabilities": dict, "metrics": dict,
    "request": dict, "response": dict, "ms": int} or None.
    """
    if not models:
        return None
    api_key = config_api_key()
    if not api_key:
        return None

    started = time.time()
    request = {
        "model": JEV_MODEL,
        "state": {
            "request": prompt,
            "session": {"current_model": current, "context_tokens": context_tokens},
            "environment": {"available_models": [m["id"] for m in models]},
        },
        "questions": {**QUESTIONS, "model": question_for_models(models)},
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    deadline = THRESHOLDS.jev_deadline_ms / 1000.0
    attempt = 0
    result: dict | None = None
    err: Exception | None = None
    while True:
        remaining = deadline - (time.time() - started)
        if remaining <= 0:
            err = TimeoutError("jev_deadline_exceeded")
            break
        timeout_s = min(THRESHOLDS.jev_timeout_ms / 1000.0, remaining)
        result, err = _post_with_wall_clock_timeout(request, headers, timeout_s)
        if err is None or _is_client_error(err):
            break  # success, or a 4xx (bad key, bad request) that a retry cannot fix
        attempt += 1
        if attempt > THRESHOLDS.jev_max_retries or time.time() - started >= deadline:
            break

    ms = int((time.time() - started) * 1000)
    if err is not None or not isinstance(result, dict):
        log(f"routing failed, keeping {current}: {err}")
        return None

    try:
        answers = result["answers"]
        answer = answers["model"]
        task_complexity = answers["task_complexity"]["score"]
        reasoning_required = answers["reasoning_required"]["score"]
        tool_complexity = answers["tool_complexity"]["score"]
    except (KeyError, TypeError) as exc:
        log(f"routing failed, keeping {current}: malformed Jev response ({exc})")
        return None

    return {
        **answer,
        "request": request,
        "response": result,
        "metrics": {
            "taskComplexity": task_complexity / COMPLEXITY_MAX_SCORE,
            "reasoningRequired": reasoning_required / COMPLEXITY_MAX_SCORE,
            "toolComplexity": tool_complexity / COMPLEXITY_MAX_SCORE,
            "contextSize": min(context_tokens / CONTEXT_WINDOW_TOKENS, 1),
        },
        "ms": ms,
    }
