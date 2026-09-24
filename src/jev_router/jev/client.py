"""JEV decision client; sole reader of TYPESAFE_API_KEY. Stdlib urllib with timeout/deadline."""
from __future__ import annotations
import json, os, threading, time, urllib.request
from jev_router.jev.normalize import normalize_jev_payload
from jev_router.jev.schema import JEVDecision

_ENDPOINT = os.environ.get("JEV_ENDPOINT", "https://api.typesafe.ai/v1/systemone")

class JevClient:
    def __init__(self, timeout_ms: int = 1500, deadline_ms: int = 3000, max_retries: int = 1):
        self.timeout_s = timeout_ms / 1000.0
        self.deadline_s = deadline_ms / 1000.0
        self.max_retries = max_retries

    def _headers(self) -> dict | None:
        key = os.environ.get("TYPESAFE_API_KEY")
        if not key:
            return None
        return {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}

    def _request_once(self, payload: dict, headers: dict, wall_clock_timeout: float):
        """Run one HTTP attempt on a daemon thread, bounded by an actual wall-clock deadline.

        urlopen's own `timeout` only bounds individual socket operations (connect, each
        read) -- a request whose DNS/connect/TLS/read steps are each fast but add up can run
        far longer than that. Joining with a wall-clock timeout on a daemon thread makes the
        deadline real without hanging process exit if the thread is still stuck.
        """
        result: dict = {}
        def target():
            try:
                req = urllib.request.Request(_ENDPOINT, data=json.dumps(payload).encode(),
                                             headers=headers, method="POST")
                with urllib.request.urlopen(req, timeout=self.timeout_s) as resp:
                    result["raw"] = json.loads(resp.read().decode() or "{}")
            except Exception as e:
                result["error"] = e
        t = threading.Thread(target=target, daemon=True)
        t.start()
        t.join(wall_clock_timeout)
        if t.is_alive():
            return None, TimeoutError("wall_clock_deadline_exceeded")
        if "error" in result:
            return None, result["error"]
        return result.get("raw"), None

    def ask(self, payload: dict) -> tuple[JEVDecision | None, int, str | None]:
        headers = self._headers()
        if headers is None:
            return None, 0, "missing_api_key"
        start = time.time()
        attempt = 0
        while True:
            remaining = self.deadline_s - (time.time() - start)
            if remaining <= 0:
                return None, int((time.time() - start) * 1000), "deadline_exceeded"
            raw, err = self._request_once(payload, headers, remaining)
            if err is None:
                ms = int((time.time() - start) * 1000)
                return normalize_jev_payload(raw, ms), ms, None
            attempt += 1
            if attempt > self.max_retries or time.time() - start >= self.deadline_s:
                return None, int((time.time() - start) * 1000), f"jev_error: {type(err).__name__}"
