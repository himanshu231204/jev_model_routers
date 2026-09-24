# Agent Adapters

> Source: `ARCHITECTURE.md` (§7, §8, §9, §33, §34, §35, §36, §37, §38, §39, §40) — verbatim split, do not edit here; propose changes against the source section.

> Back to index: [docs/README.md](./README.md)

---

# 7. Agent Adapter Layer

The adapter layer is the most important extensibility mechanism.

Each coding agent gets an implementation of the common interface.

## 7.1 Adapter contract

```python
from typing import Protocol


class AgentAdapter(Protocol):
    name: str

    def detect(self) -> bool:
        """Return True when this adapter can operate in the environment."""
        ...

    def capabilities(self):
        """Return adapter capabilities."""
        ...

    def start(self, config):
        """Start or attach to the coding agent."""
        ...

    def normalize_request(self, raw_request):
        """Convert the agent-native request to NormalizedRequest."""
        ...

    def apply_model(self, raw_request, model):
        """Apply the chosen model in the agent-native request format."""
        ...

    def forward(self, request):
        """Forward request to the original upstream endpoint."""
        ...

    def display_decision(self, decision):
        """Display routing information in the native agent UX where possible."""
        ...

    def is_new_turn(self, request) -> bool:
        """Detect whether the request begins a fresh user turn."""
        ...

    def conversation_key(self, request) -> str:
        """Return a stable key for conversation/agent state."""
        ...
```

---

---

# 8. Agent Adapter Types

Not every agent should be integrated the same way.

Use three integration strategies.

## 8.1 Wrapper adapter

```text
jev-router
   ↓
launch agent
   ↓
agent connects normally
```

Best when the CLI exposes a clean configurable endpoint/provider.

Example:

```bash
jev-router claude
```

---

## 8.2 Reverse proxy adapter

```text
Agent
  ↓
localhost proxy
  ↓
JEV Router
  ↓
upstream provider
```

The router intercepts model requests and rewrites the selected model.

Best when the agent supports a configurable `base_url`/provider endpoint.

---

## 8.3 SDK adapter

For agents embedded as Python/TypeScript libraries:

```text
Application
   ↓
Agent SDK
   ↓
JEV middleware
   ↓
Model client
```

This is especially useful for DeepAgents-style applications where the user owns the runtime.

---

---

# 9. Supported Agent Strategy

The initial adapter matrix should look like this:

| Agent | Integration target | Preferred adapter | Main responsibility |
|---|---|---|---|
| Claude Code | CLI/API request path | Proxy + wrapper | Preserve native CLI while routing model requests |
| OpenAI Codex | CLI/provider path | Provider injection + proxy | Route Responses/API model selection |
| OpenCode | Provider configuration | Custom provider/baseURL adapter | Inject JEV-controlled provider/model |
| DeepAgents | Python SDK/runtime | Middleware / model wrapper | Intercept model invocation |
| Hermes Agent | Provider/model runtime | Provider/baseURL adapter | Route configured provider/model |
| Custom agent | API/SDK | Generic adapter SDK | Normalize arbitrary agent request |

The exact wire-level implementation must remain isolated inside each adapter because coding agents evolve independently.

OpenCode currently supports provider configuration and custom `baseURL` settings, making provider-level integration a natural adapter boundary. citeturn817834search2 Hermes similarly separates provider/runtime resolution from model selection and supports custom/OpenAI-compatible endpoints. citeturn817834search0turn817834search1

---

---

# 33. Agent Capability Contract

Every adapter declares what it can and cannot do.

```python
@dataclass
class AgentCapabilities:
    supports_proxy: bool
    supports_custom_base_url: bool
    supports_custom_provider: bool
    supports_model_override: bool
    supports_streaming_intercept: bool
    supports_sdk_middleware: bool
    supports_native_status_display: bool
    supports_subagent_identification: bool
```

This allows the router to choose the correct integration strategy automatically.

---

---

# 34. Agent Adapter Example: Claude Code

Conceptually:

```text
Claude Code
   ↓
Claude Adapter
   ↓
recognize fresh user request
   ↓
normalize Anthropic-style request
   ↓
JEV Router
   ↓
chosen Claude model
   ↓
rewrite request
   ↓
Anthropic endpoint
```

The Claude adapter should own all Claude-specific compatibility details.

Examples of adapter-only logic:

- request schema normalization
- Claude-specific model IDs
- Claude-specific thinking/effort capability handling
- session metadata extraction
- auxiliary requests
- Claude-native status display

Those must **not** leak into core policy code.

---

---

# 35. Agent Adapter Example: OpenAI Codex

Conceptually:

```text
Codex
  ↓
Codex Adapter
  ↓
normalize Responses-style request
  ↓
JEV Router
  ↓
resolved OpenAI model
  ↓
rewrite request/provider
  ↓
OpenAI
```

Codex-specific logic belongs under:

```text
adapters/codex/
```

not under:

```text
core/policy/
```

---

---

# 36. Agent Adapter Example: OpenCode

OpenCode provides a provider-oriented configuration model and supports custom base URLs, so the adapter should prefer a **provider injection / proxy boundary** where possible. citeturn817834search2

Conceptually:

```text
OpenCode
   ↓
JEV provider
   ↓
JEV Router
   ↓
selected provider/model
```

The OpenCode adapter should translate:

```text
JEV capability
       ↓
OpenCode provider + model identifier
```

without changing core routing logic.

---

---

# 37. Agent Adapter Example: DeepAgents

For DeepAgents-based Python applications, the preferred integration is middleware/model abstraction rather than pretending it is a CLI.

Conceptually:

```python
agent = create_deep_agent(
    model=JEVModelRouter(...)
)
```

Or:

```python
model = JevRoutedModel(
    candidates=[...]
)

agent = create_agent(model=model)
```

The adapter should intercept the model invocation boundary.

It should not intercept individual tool calls unless necessary.

---

---

# 38. Agent Adapter Example: Hermes

Hermes exposes provider/model selection and can work with custom/provider endpoints. Its runtime separates provider resolution, API mode, base URL, authentication, and model selection. citeturn817834search1turn817834search11

Therefore the Hermes adapter should preferably operate at the **provider/model resolution boundary**.

```text
Hermes
  ↓
provider/model selection
  ↓
JEV adapter
  ↓
model resolution
  ↓
provider
```

The adapter must preserve Hermes-native provider semantics where possible.

---

---

# 39. Generic Adapter SDK

Eventually allow third-party integrations.

Example:

```python
from jev_router.adapters import AgentAdapter


class MyCodingAgentAdapter(AgentAdapter):
    name = "my-agent"

    def detect(self):
        return shutil.which("my-agent") is not None

    def normalize_request(self, request):
        ...

    def apply_model(self, request, model):
        ...
```

This becomes the plugin API.

---

---

# 40. Plugin Architecture

Recommended plugin structure:

```text
plugins/
├── agents/
│   ├── claude_code/
│   ├── codex/
│   ├── opencode/
│   ├── deepagents/
│   └── hermes/
│
└── providers/
    ├── anthropic/
    ├── openai/
    ├── google/
    ├── openrouter/
    └── custom/
```

Each plugin should expose a manifest:

```yaml
name: opencode
version: 1
kind: agent
capabilities:
  proxy: true
  custom_provider: true
  sdk_middleware: false
```

---
