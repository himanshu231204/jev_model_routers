"""OpenAI provider: endpoint, authentication, request translation, and streaming semantics."""
from __future__ import annotations
class OpenAIProvider:
    name = "openai"
    def endpoint(self) -> str:
        return "https://api.openai.com/v1/responses"
    def translate(self, request: dict, model: str) -> dict:
        body = dict(request.get("body", {})); body["model"] = model
        return {"url": self.endpoint(), "body": body, "stream": body.get("stream", False)}
    def parse_response(self, raw: dict) -> dict:
        return {"content": str(raw.get("output_text", raw.get("content", ""))), "model": raw.get("model", "")}
