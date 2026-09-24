"""OpenRouter provider: endpoint, authentication, request translation, and streaming semantics."""
from __future__ import annotations
class OpenRouterProvider:
    name = "openrouter"
    def endpoint(self) -> str:
        return "https://openrouter.ai/api/v1/chat/completions"
    def translate(self, request: dict, model: str) -> dict:
        body = dict(request.get("body", {})); body["model"] = model
        return {"url": self.endpoint(), "body": body}
    def parse_response(self, raw: dict) -> dict:
        return {"content": str(raw.get("content", "")), "model": raw.get("model", "")}
