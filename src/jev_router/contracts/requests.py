"""Normalized routing request shared by all agent adapters."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Message:
    role: str
    content: str


@dataclass
class ToolMetadata:
    name: str
    category: str = "general"
    stateful: bool = False
    destructive: bool = False
    network: bool = False


@dataclass
class RepositoryContext:
    root: str | None = None
    language: list[str] = field(default_factory=list)
    framework: list[str] = field(default_factory=list)
    file_count: int | None = None
    changed_files: int | None = None
    git_branch: str | None = None
    dirty: bool | None = None
    project_type: str | None = None


@dataclass
class NormalizedRequest:
    request_id: str
    agent: str
    agent_version: str | None = None
    session_id: str = ""
    conversation_id: str = ""
    turn_id: str = ""
    prompt: str = ""
    messages: list[Message] = field(default_factory=list)
    current_model: str | None = None
    available_models: list[str] = field(default_factory=list)
    tools: list[ToolMetadata] = field(default_factory=list)
    tool_count: int = 0
    context_tokens: int | None = None
    max_context_tokens: int | None = None
    repository: RepositoryContext | None = None
    environment: dict[str, Any] | None = None
    stream: bool = False
    is_subagent: bool = False
    is_new_turn: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)
