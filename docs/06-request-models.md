# Request Models and Routing Context

> Source: `ARCHITECTURE.md` (§10, §11, §12, §13) — verbatim split, do not edit here; propose changes against the source section.

> Back to index: [docs/README.md](./README.md)

---

# 10. Normalized Request Model

Every adapter must convert its native request into the same internal structure.

```python
@dataclass
class NormalizedRequest:
    request_id: str
    agent: str
    agent_version: str | None

    session_id: str
    conversation_id: str
    turn_id: str

    prompt: str
    messages: list[Message]

    current_model: str | None
    available_models: list[str]

    tools: list[ToolMetadata]
    tool_count: int

    context_tokens: int | None
    max_context_tokens: int | None

    repository: RepositoryContext | None
    environment: EnvironmentContext | None

    stream: bool
    is_subagent: bool
    is_new_turn: bool

    metadata: dict[str, Any]
```

The normalized request is an **internal representation** only.

It must never be assumed that all agents can provide every field.

Missing information is represented explicitly:

```json
{
  "context_tokens": null,
  "repository": null
}
```

not fabricated values.

---

---

# 11. Repository Context

Coding tasks are unusually sensitive to repository context.

The router should optionally receive lightweight metadata:

```python
@dataclass
class RepositoryContext:
    root: str | None
    language: list[str]
    framework: list[str]
    file_count: int | None
    changed_files: int | None
    git_branch: str | None
    dirty: bool | None
    project_type: str | None
```

Avoid sending the repository itself to JEV by default.

The router should primarily use:

- prompt
- available models
- context size
- tool complexity
- agent metadata
- optional repository summary

Privacy should be a first-class feature.

---

---

# 12. Tool Metadata

Tool complexity should be represented without exposing sensitive tool contents unnecessarily.

```python
@dataclass
class ToolMetadata:
    name: str
    category: str
    stateful: bool
    destructive: bool
    network: bool
```

Example:

```json
{
  "name": "terminal",
  "category": "execution",
  "stateful": true,
  "destructive": true,
  "network": false
}
```

This lets JEV understand that:

```text
"Rename this variable"
```

is different from:

```text
"Migrate the entire production database and update all services"
```

without needing raw tool definitions.

---

---

# 13. Routing Context

`RoutingContext` is the canonical input to the routing engine.

```python
@dataclass
class RoutingContext:
    task: TaskContext
    session: SessionContext
    environment: EnvironmentContext
    capabilities: AgentCapabilities
    candidates: list[ModelCandidate]
```

## 13.1 TaskContext

```python
@dataclass
class TaskContext:
    prompt: str
    task_type: str | None
    complexity_hint: float | None
    reasoning_hint: float | None
    tool_complexity_hint: float | None
```

## 13.2 SessionContext

```python
@dataclass
class SessionContext:
    session_id: str
    conversation_id: str
    turn_id: str
    current_model: str | None
    context_tokens: int | None
    is_new_turn: bool
    is_subagent: bool
```

---
