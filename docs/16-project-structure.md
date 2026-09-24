# Project Structure and Versioning

> Source: `ARCHITECTURE.md` (§55, §56, §57, §90, §91, §92, §93, §94) — verbatim split, do not edit here; propose changes against the source section.

> Back to index: [docs/README.md](./README.md)

---

# 55. Project Structure

Recommended repository layout:

```text
jev_model_router/
│
├── pyproject.toml
├── README.md
├── LICENSE
├── ARCHITECTURE.md
├── CHANGELOG.md
├── CONTRIBUTING.md
├── SECURITY.md
│
├── src/
│   └── jev_router/
│       │
│       ├── __init__.py
│       ├── version.py
│       │
│       ├── cli/
│       │   ├── main.py
│       │   ├── run.py
│       │   ├── agents.py
│       │   ├── models.py
│       │   ├── status.py
│       │   ├── explain.py
│       │   └── doctor.py
│       │
│       ├── core/
│       │   ├── router.py
│       │   ├── policy.py
│       │   ├── decision.py
│       │   ├── classifier.py
│       │   ├── resolver.py
│       │   ├── overrides.py
│       │   └── lifecycle.py
│       │
│       ├── contracts/
│       │   ├── requests.py
│       │   ├── responses.py
│       │   ├── models.py
│       │   ├── agents.py
│       │   └── events.py
│       │
│       ├── adapters/
│       │   ├── base.py
│       │   ├── registry.py
│       │   ├── claude_code/
│       │   │   ├── adapter.py
│       │   │   ├── proxy.py
│       │   │   ├── parser.py
│       │   │   └── compatibility.py
│       │   ├── codex/
│       │   │   ├── adapter.py
│       │   │   ├── proxy.py
│       │   │   └── parser.py
│       │   ├── opencode/
│       │   │   ├── adapter.py
│       │   │   └── config.py
│       │   ├── deepagents/
│       │   │   ├── adapter.py
│       │   │   └── middleware.py
│       │   └── hermes/
│       │       ├── adapter.py
│       │       └── config.py
│       │
│       ├── providers/
│       │   ├── base.py
│       │   ├── registry.py
│       │   ├── anthropic.py
│       │   ├── openai.py
│       │   ├── google.py
│       │   ├── openrouter.py
│       │   ├── ollama.py
│       │   └── custom.py
│       │
│       ├── jev/
│       │   ├── client.py
│       │   ├── schema.py
│       │   ├── questions.py
│       │   └── normalize.py
│       │
│       ├── transport/
│       │   ├── base.py
│       │   ├── http.py
│       │   ├── sse.py
│       │   └── websocket.py
│       │
│       ├── state/
│       │   ├── store.py
│       │   ├── memory.py
│       │   └── sqlite.py
│       │
│       ├── config/
│       │   ├── loader.py
│       │   ├── schema.py
│       │   └── defaults.py
│       │
│       ├── observability/
│       │   ├── logging.py
│       │   ├── metrics.py
│       │   ├── events.py
│       │   └── tracing.py
│       │
│       └── security/
│           ├── redaction.py
│           ├── secrets.py
│           └── validation.py
│
├── configs/
│   ├── default.yaml
│   └── example.yaml
│
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── contract/
│   ├── adapters/
│   ├── routing/
│   └── fixtures/
│
├── docs/
│   ├── architecture/
│   ├── adapters/
│   ├── providers/
│   ├── development/
│   └── troubleshooting/
│
└── scripts/
    ├── dev.py
    └── release.py
```

---

---

# 56. Dependency Direction

The dependency graph should be intentionally one-directional.

```text
CLI
 ↓
Adapters
 ↓
Core
 ↓
Contracts
```

Providers and transports should be injected into the core rather than imported directly by policy code.

Bad:

```python
# core/policy.py
from adapters.claude_code import ClaudeCodeAdapter
```

Good:

```python
# core/policy.py
from contracts.models import ModelSpec
```

The core should work with abstract contracts only.

---

---

# 57. Interface Contracts

## Router

```python
class Router:
    async def route(self, request: NormalizedRequest) -> RoutingDecision:
        ...
```

## Policy

```python
class Policy:
    def evaluate(
        self,
        request: NormalizedRequest,
        jev: JEVDecision,
    ) -> PolicyDecision:
        ...
```

## Resolver

```python
class ModelResolver:
    def resolve(
        self,
        request: NormalizedRequest,
        decision: PolicyDecision,
    ) -> ModelResolution:
        ...
```

## Adapter

```python
class AgentAdapter:
    def normalize_request(self, raw_request): ...
    def apply_model(self, raw_request, model): ...
    def is_new_turn(self, raw_request): ...
```

---

---

# 90. Example Future Plugin

A third-party developer should be able to install:

```bash
pip install jev-router-agent-myagent
```

and the router discovers:

```text
myagent adapter registered
```

Then:

```bash
jev-router myagent
```

No core change required.

---

---

# 91. Versioning Strategy

Use semantic versioning:

```text
MAJOR.MINOR.PATCH
```

Important versioned contracts:

```text
Adapter API
Plugin API
NormalizedRequest schema
ModelSpec schema
RoutingDecision schema
```

Changing these should have migration notes.

---

---

# 92. Compatibility Layer

Agent protocols are unstable compared to the router's internal API.

Therefore introduce:

```text
adapter compatibility versions
```

Example:

```python
ClaudeCodeAdapter(
    protocol_version="2026-09"
)
```

Do not spread protocol-version conditionals through the core.

Bad:

```python
if claude_version >= ...:
    ...
```

inside `core/router.py`.

Good:

```text
adapters/claude_code/compatibility.py
```

---

---

# 93. Documentation Structure

Recommended docs:

```text
README.md
    ↓
quick start

ARCHITECTURE.md
    ↓
complete design

/docs/adapters/
    ↓
agent integration guides

/docs/providers/
    ↓
provider configuration

/docs/development/
    ↓
contributor architecture

/docs/troubleshooting/
    ↓
diagnostics
```

---

---

# 94. README Positioning

Suggested product statement:

> **JEV Model Router is an agent-agnostic intelligent model router for coding agents. It routes each coding task to an appropriate model while preserving the native agent workflow.**

Example:

```text
Claude Code ─┐
Codex ───────┤
OpenCode ────┤
DeepAgents ──┤──→ JEV Model Router ──→ best available model
Hermes ──────┤
Custom ──────┘
```

---
