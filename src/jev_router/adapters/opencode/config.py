from __future__ import annotations
def provider_entry(model: str) -> dict:
    provider, _, name = model.partition("/")
    return {"provider": provider or "anthropic", "model": name or model}
