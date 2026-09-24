"""Stdlib HTTP forwarding transport (urllib, no deps)."""
from __future__ import annotations
import json, urllib.request
class HttpTransport:
    def __init__(self, base_url: str, headers: dict | None = None):
        self.base_url = base_url.rstrip("/"); self.headers = headers or {}
    def send(self, request: dict) -> dict:
        data = json.dumps(request.get("body", {})).encode()
        req = urllib.request.Request(self.base_url + request.get("path", "/"), data=data,
                                     headers={"Content-Type": "application/json", **self.headers}, method="POST")
        with urllib.request.urlopen(req, timeout=30) as resp:
            return {"status": resp.status, "body": resp.read().decode()}
