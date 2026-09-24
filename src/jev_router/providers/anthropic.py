"""Anthropic provider: endpoint, authentication, request translation, and streaming semantics."""
from __future__ import annotations
class AnthropicProvider:
    name = "anthropic"
    def endpoint(self) -> str:
        return "https://api.anthropic.com/v1/messages"
    def translate(self, request: dict, model: str) -> dict:
        body = dict(request.get("body", {})); body["model"] = model
        return {"url": self.endpoint(), "body": body, "stream": body.get("stream", False)}
    def parse_response(self, raw: dict) -> dict:
        return {"content": str(raw.get("content", "")), "model": raw.get("model", "")}
