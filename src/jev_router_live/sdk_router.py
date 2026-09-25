"""Opt-in Jev client (``JEV_CLIENT=sdk``) built on TypeSafe's official ``typesafe-sdk``.

Asks the same questions and returns the same shape as ``stdlib_router.stdlib_ask_jev``, under
the same rules: one retry for timeouts/network/5xx only, a hard wall-clock deadline for the
whole call, and ``None`` (fail open) on any failure.
"""
from __future__ import annotations

import logging
import time

from jev_router_live.config import (
    COMPLEXITY_MAX_SCORE,
    CONTEXT_WINDOW_TOKENS,
    JEV_MODEL,
    QUESTIONS,
    THRESHOLDS,
    question_for_models,
)
from jev_router_live.config import api_key as config_api_key
from jev_router_live.log import debug, log
from jev_router_live import stdlib_router
from jev_router_live.stdlib_router import call_with_deadline

_SYSTEM_ONE_PATH = "/v1/systemone"
_SCORE_QUESTIONS = ("task_complexity", "reasoning_required", "tool_complexity")


def _base_url() -> str | None:
    """API root for the SDK, which appends ``/v1/systemone`` itself. ``JEV_ENDPOINT`` (the full
    URL, shared with the stdlib client and ``scripts/fake_jev.py``) wins when set; otherwise
    ``None`` lets the SDK resolve ``TYPESAFE_BASE_URL`` or its default."""
    endpoint = stdlib_router._ENDPOINT.rstrip("/")
    if endpoint.endswith(_SYSTEM_ONE_PATH):
        return endpoint[: -len(_SYSTEM_ONE_PATH)] or None
    return None


def _retry_policy(sdk):
    """Mirror of the stdlib client's retry rule. The SDK's defaults would also retry 408/429,
    honor ``Retry-After`` (an arbitrarily long sleep) and back off 0.5 s, none of which fit a
    3 s routing deadline. ``timeout`` here is the SDK's total retry budget per call."""
    return sdk.RetryPolicy(
        max_retries=THRESHOLDS.jev_max_retries,
        backoff_initial=0,
        backoff_max=0,
        http_statuses=set(range(500, 600)),
        respect_retry_after=False,
        timeout=THRESHOLDS.jev_deadline_ms / 1000.0,
    )


def sdk_ask_jev(*, prompt: str, current: str, context_tokens: int, models: list[dict]) -> dict | None:
    """Asks Jev which exact model fits this prompt through ``typesafe-sdk``. Returns the same
    dict as ``stdlib_ask_jev``, or None on any failure (policy then keeps the current model)."""
    try:
        import typesafe_sdk as sdk
    except ImportError:
        log("JEV_CLIENT=sdk but typesafe_sdk is not installed (pip install 'jev-model-router[typesafe]'); not routing")
        return None
    if not models:
        return None
    key = config_api_key()
    if not key:
        return None
    logging.getLogger("typesafe_sdk").setLevel(logging.WARNING)

    started = time.time()
    state = {
        "request": prompt,
        "session": {"current_model": current, "context_tokens": context_tokens},
        "environment": {"available_models": [m["id"] for m in models]},
    }
    model_question = question_for_models(models)
    questions = {
        **{name: sdk.Score(instructions=q["instructions"], criteria=q["criteria"]) for name, q in QUESTIONS.items()},
        "model": sdk.Choice(instructions=model_question["instructions"], criteria=model_question["criteria"]),
    }
    request = {"model": JEV_MODEL, "state": state, "questions": {**QUESTIONS, "model": model_question}}

    def call():
        with sdk.TypeSafeClient(
            api_key=key,
            base_url=_base_url(),
            model=JEV_MODEL,
            retry=_retry_policy(sdk),
            timeout=THRESHOLDS.jev_timeout_ms / 1000.0,  # per HTTP attempt; the SDK default is 10 s
        ) as client:
            return client.system_one(state, questions)

    result, err = call_with_deadline(call, THRESHOLDS.jev_deadline_ms / 1000.0)
    ms = int((time.time() - started) * 1000)
    if err is not None:
        # Exception type only: SDK error messages can echo the response body.
        log(f"routing failed (sdk), keeping {current}: {type(err).__name__}")
        return None

    try:
        answer = result.choices["model"]
        scores = {name: result.scores[name].score for name in _SCORE_QUESTIONS}
        raw = result.raw_http_response
        response = raw.json()
    except Exception as exc:  # noqa: BLE001 - any unexpected shape fails open
        log(f"routing failed (sdk), keeping {current}: malformed Jev response ({type(exc).__name__}: {exc})")
        return None
    # `result.request_id` raises when the header is absent, so read it directly.
    debug(f"jev (sdk) request_id={raw.headers.get('x-typesafe-request-id')} model={result.model}")

    return {
        "choice": answer.choice,
        "confidence": answer.confidence,
        "probabilities": dict(answer.probabilities),
        "request": request,
        "response": response,
        "metrics": {
            "taskComplexity": scores["task_complexity"] / COMPLEXITY_MAX_SCORE,
            "reasoningRequired": scores["reasoning_required"] / COMPLEXITY_MAX_SCORE,
            "toolComplexity": scores["tool_complexity"] / COMPLEXITY_MAX_SCORE,
            "contextSize": min(context_tokens / CONTEXT_WINDOW_TOKENS, 1),
        },
        "ms": ms,
    }
