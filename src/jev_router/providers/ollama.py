"""Ollama provider: endpoint, authentication, request translation, and streaming semantics."""
from __future__ import annotations
class OllamaProvider:
    name = "ollama"
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url
    def endpoint(self) -> str:
        return f"{self.base_url}/api/chat"
    def translate(self, request: dict, model: str) -> dict:
        body = dict(request.get("body", {})); body["model"] = model.split("/")[-1]
        return {"url": self.endpoint(), "body": body}
    def parse_response(self, raw: dict) -> dict:
        return {"content": str(raw.get("message", raw.get("content", ""))), "model": raw.get("model", "")}
