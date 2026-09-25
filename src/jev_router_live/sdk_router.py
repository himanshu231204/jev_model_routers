"""Best-effort SDK path for live proxy; raw-dict questions, fail-open None."""
from __future__ import annotations
import logging, os, time
def sdk_ask_jev(*, prompt, current, context_tokens, models):
    start = time.time()
    from jev_router_live.log import log
    try:
        import typesafe_sdk
    except ImportError:
        log("JEV_CLIENT=sdk but typesafe_sdk is not installed (pip install 'jev-model-router[typesafe]'); not routing")
        return None
    from jev_router_live.config import api_key
    key = api_key()
    if not key or not models:
        return None
    logging.getLogger("typesafe_sdk").setLevel(logging.WARNING)
    try:
        from jev_router_live.config import QUESTIONS, THRESHOLDS, question_for_models, CONTEXT_WINDOW_TOKENS, JEV_MODEL
        questions = {**QUESTIONS, "model": question_for_models(models)}
        retry = typesafe_sdk.RetryPolicy(max_retries=THRESHOLDS.jev_max_retries, timeout=THRESHOLDS.jev_timeout_ms / 1000.0)
        base = os.environ.get("JEV_BASE_URL") or "https://api.typesafe.ai"
        with typesafe_sdk.TypeSafeClient(api_key=key, base_url=base, model=JEV_MODEL, retry=retry) as client:
            state = {"request": prompt, "session": {"current_model": current, "context_tokens": context_tokens},
                     "environment": {"available_models": [m["id"] for m in models]}}
            result = client.system_one(state, questions)
        ans = result.choices["model"]
        return {"choice": ans.choice, "confidence": float(getattr(ans, "confidence", 0.0)),
                "probabilities": dict(getattr(ans, "probabilities", {}) or {}),
                "metrics": {"taskComplexity": 0.5, "reasoningRequired": 0.5, "toolComplexity": 0.5,
                            "contextSize": min(context_tokens / CONTEXT_WINDOW_TOKENS, 1)},
                "request": {"state": state, "questions": questions}, "response": {}, "ms": int((time.time() - start) * 1000)}
    except Exception as exc:  # noqa: BLE001 - fail open, but visibly
        log(f"routing failed (sdk), keeping {current}: {type(exc).__name__}")
        return None
