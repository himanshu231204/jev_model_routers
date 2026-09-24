"""Model specification contract: normalized model identity and capabilities."""
from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class ModelCapabilities:
    coding: int = 5
    reasoning: int = 5
    tool_use: int = 5
    context: int = 5
    speed: int = 5
    cost: int = 5


@dataclass
class ModelSpec:
    id: str
    provider: str
    family: str = ""
    tier: str = "balanced"
    capabilities: ModelCapabilities = field(default_factory=ModelCapabilities)
    context_window: int | None = None
    tool_support: bool = True
    streaming: bool = True
    vision: bool = False
    aliases: list[str] = field(default_factory=list)
    enabled: bool = True
    compatible_agents: list[str] = field(default_factory=list)
