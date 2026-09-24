"""Normalized response contract shared by providers and adapters."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ProviderResponse:
    request_id: str
    model: str
    content: str = ""
    is_streaming: bool = False
    finish_reason: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
