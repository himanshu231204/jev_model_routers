"""Google provider: endpoint, authentication, request translation, and streaming semantics."""
from __future__ import annotations
class GoogleProvider:
    name = "google"
    def endpoint(self) -> str:
        return "https://generativelanguage.googleapis.com/v1beta/models"
    def translate(self, request: dict, model: str) -> dict:
        return {"url": f"{self.endpoint()}/{model}:generateContent", "body": request.get("body", {})}
    def parse_response(self, raw: dict) -> dict:
        return {"content": str(raw.get("content", "")), "model": raw.get("model", "")}
