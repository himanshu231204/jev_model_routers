"""JEV decision client; sole reader of JEV_API_KEY. Stdlib urllib with timeout/deadline."""
from __future__ import annotations
import json, os, time, urllib.request
from jev_router.jev.normalize import normalize_jev_payload
from jev_router.jev.schema import JEVDecision

_ENDPOINT = os.environ.get("JEV_ENDPOINT", "https://openrouter.ai/api/alpha/decisions")

class JevClient:
    def __init__(self, timeout_ms: int = 1500, deadline_ms: int = 3000, max_retries: int = 1):
        self.timeout_s = timeout_ms / 1000.0
        self.deadline_s = deadline_ms / 1000.0
        self.max_retries = max_retries

    def _headers(self) -> dict | None:
        key = os.environ.get("JEV_API_KEY")
        if not key:
            return None
        return {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}

    def ask(self, payload: dict) -> tuple[JEVDecision | None, int, str | None]:
        headers = self._headers()
        if headers is None:
            return None, 0, "missing_api_key"
        start = time.time()
        attempt = 0
        while True:
            if time.time() - start > self.deadline_s:
                return None, int((time.time() - start) * 1000), "deadline_exceeded"
            try:
                req = urllib.request.Request(_ENDPOINT, data=json.dumps(payload).encode(), headers=headers, method="POST")
                with urllib.request.urlopen(req, timeout=self.timeout_s) as resp:
                    raw = json.loads(resp.read().decode() or "{}")
                ms = int((time.time() - start) * 1000)
                return normalize_jev_payload(raw, ms), ms, None
            except Exception as e:
                attempt += 1
                if attempt > self.max_retries or time.time() - start > self.deadline_s:
                    return None, int((time.time() - start) * 1000), f"jev_error: {type(e).__name__}"
