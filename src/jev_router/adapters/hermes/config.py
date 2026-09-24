from __future__ import annotations
def split_model(model: str) -> tuple[str, str]:
    p, _, m = model.partition(":")
    return (p if m else "default", m or p)
