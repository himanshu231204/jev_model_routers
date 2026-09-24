"""Custom OpenAI-compatible provider with a user-configured endpoint and model catalog."""
from __future__ import annotations
class CustomProvider:
    name = "custom"
    def __init__(self, base_url: str = "", api_key_env: str = ""):
        self.base_url = base_url; self.api_key_env = api_key_env
    def endpoint(self) -> str:
        return self.base_url
    def translate(self, request: dict, model: str) -> dict:
        body = dict(request.get("body", {})); body["model"] = model
        return {"url": self.base_url, "body": body}
    def parse_response(self, raw: dict) -> dict:
        return {"content": str(raw.get("content", "")), "model": raw.get("model", "")}
