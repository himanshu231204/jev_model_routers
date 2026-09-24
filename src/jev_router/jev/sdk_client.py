"""Optional SDK transport; lazy import so stdlib default has zero extra deps."""
from __future__ import annotations
import logging, os, time
from jev_router.jev.normalize import normalize_jev_payload

_ENDPOINT_DEFAULT = "https://api.typesafe.ai/v1/systemone"


class SdkJevClient:
    def __init__(self, timeout_ms: int = 1500, deadline_ms: int = 3000, max_retries: int = 1):
        self.timeout_s = timeout_ms / 1000.0
        self.deadline_s = deadline_ms / 1000.0
        self.max_retries = max_retries

    def _endpoint(self) -> str:
        return os.environ.get("JEV_ENDPOINT") or os.environ.get("TYPESAFE_BASE_URL") or _ENDPOINT_DEFAULT

    def ask(self, payload: dict):
        start = time.time()
        ms = lambda: int((time.time() - start) * 1000)
        try:
            import typesafe_sdk
        except ImportError as e:
            return None, ms(), f"jev_error: missing_extra:{type(e).__name__}"
        key = os.environ.get("TYPESAFE_API_KEY")
        if not key:
            return None, 0, "missing_api_key"
        logging.getLogger("typesafe_sdk").setLevel(logging.WARNING)
        try:
            tier_q = (payload.get("questions") or {}).get("tier", {}) or {}
            question = typesafe_sdk.Choice(
                instructions=tier_q.get("instructions", "pick the model tier"),
                criteria=tier_q.get("criteria") or {"fast": None, "balanced": None, "strong": None},
            )
            retry = typesafe_sdk.RetryPolicy(max_retries=self.max_retries, timeout=self.timeout_s)
            with typesafe_sdk.TypeSafeClient(api_key=key, base_url=self._endpoint(),
                                             model=payload.get("model") or "jev-latest",
                                             retry=retry) as client:
                result = client.system_one(payload.get("state") or {}, {"tier": question})
            return normalize_jev_payload({"answers": {"tier": {"type": "choice",
                "choice": result.choices["tier"].choice,
                "confidence": result.choices["tier"].confidence}}}, ms()), ms(), None
        except Exception as e:
            return None, ms(), f"jev_error: {type(e).__name__}"
