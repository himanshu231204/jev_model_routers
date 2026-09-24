# AGENTS.md — JEV Model Router

> This file is the operating contract for AI coding agents working on the **JEV Model Router** repository.
>
> The repository is intended to become an **agent-agnostic model-routing layer for coding agents** such as Claude Code, OpenAI Codex, OpenCode, DeepAgents-based coding agents, Hermes Agent, and future/custom agents.

---

## 1. Mission

JEV Model Router sits between a coding agent and one or more model providers.

Its responsibility is to decide **which model should handle a fresh coding turn**, while preserving the coding agent's native execution environment wherever possible.

The central architecture is:

```text
Coding Agent
    ↓
Agent Adapter
    ↓
Normalized Request
    ↓
JEV Router Core
    ↓
Routing Policy
    ↓
Model Resolver
    ↓
Agent/Provider Adapter
    ↓
Model Provider
```

Examples of supported or planned coding agents:

```text
Claude Code
OpenAI Codex
OpenCode
DeepAgents coding agents
Hermes Agent
Custom coding agents
```

The project must remain **agent-agnostic at its core**.

---


---

# 2A. JEV API Key and Routing Authority

**JEV API is mandatory for automatic routing.** The router must use the official JEV API for routing decisions rather than implementing an independent LLM classifier in the core.

## Authentication

Use the environment variable:

```text
JEV_API_KEY
```

Recommended local development configuration:

```bash
export JEV_API_KEY="..."
```

On Windows PowerShell:

```powershell
$env:JEV_API_KEY = "..."
```

A project-local `.env` may be supported by the configuration loader, but `.env` must never be committed. A user-level configuration file may also be supported if documented by the CLI.

## Key handling rules

Never:

- hard-code `JEV_API_KEY` in source code
- commit `JEV_API_KEY` to Git
- print `JEV_API_KEY` in logs
- include the key in error messages
- send the key to an agent adapter
- expose the key to a model provider unless the provider is explicitly the JEV API endpoint

The key should be read only by the JEV client/configuration layer.

Conceptually:

```text
Coding Agent
     │
     ▼
JEV Model Router
     │
     ├── normalized routing request
     │
     ▼
JEV API Client
     │
     │ Authorization: JEV_API_KEY
     ▼
JEV API
     │
     ▼
Routing Decision
```

## JEV client boundary

Keep JEV authentication isolated behind a small client interface, for example:

```python
class JEVClient:
    def route(self, request: RoutingRequest) -> JEVDecision:
        ...
```

The rest of the codebase must not manually construct JEV authorization headers or read `JEV_API_KEY` directly.

## Missing key behavior

If `JEV_API_KEY` is missing:

```text
startup
  ↓
router detects missing key
  ↓
automatic routing unavailable
  ↓
use current/default model
  ↓
continue coding session
```

The CLI should provide a clear actionable message explaining how to configure `JEV_API_KEY`, but it must not crash a running coding workflow solely because routing is unavailable.

## JEV API failure behavior

Timeouts, authentication failures, rate limits, malformed responses, and transient network failures must be handled through the fail-open policy already defined in this document.

Do not silently replace JEV with another LLM-based router. A fallback model may be selected, but the **routing authority remains JEV** whenever automatic routing is enabled and the JEV API is reachable.

## Configuration precedence

Use a deterministic configuration precedence, preferably:

```text
Explicit process environment
        ↓
CLI/config file override
        ↓
User-level JEV configuration
        ↓
Missing / disabled
```

Document the actual precedence implemented by the repository and keep it consistent across all agent adapters.

## Testing JEV authentication

Tests must not require a real API key by default. Use mocked/stubbed JEV responses for normal unit and integration tests.

Live JEV tests must be opt-in, for example:

```text
JEV_LIVE_TESTS=1
```

and must require `JEV_API_KEY` from the environment. Never place a live key in fixtures.

# 2B. Agent Integrations Require JEV Authentication

The supported coding-agent integrations are not independent routers. **Claude Code, OpenCode, Codex, DeepAgents-based integrations, Hermes Agent, and other JEV-enabled adapters must use the configured `JEV_API_KEY` to activate JEV-powered automatic model routing.**

The integration contract is:

```text
User
  │
  ▼
Coding Agent (Claude Code / OpenCode / Codex / etc.)
  │
  ▼
JEV Model Router Adapter
  │
  ├── reads JEV_API_KEY from environment/config
  │
  ▼
JEV API
  │
  ▼
Routing Decision
  │
  ▼
Native Agent Request with resolved model
```

## Claude Code integration

The Claude Code adapter must:

1. Launch or wrap the real Claude Code CLI without replacing its normal agent behavior.
2. Read `JEV_API_KEY` through the shared JEV authentication/configuration layer.
3. Send the normalized fresh-turn routing request to the JEV API.
4. Apply the returned model decision using Claude Code's supported request/model mechanism.
5. Preserve Claude Code sessions, tools, permissions, MCP behavior, and tool-loop continuity.

Example conceptual flow:

```text
claude
  ↓
JEV Claude Adapter
  ↓
JEV API (JEV_API_KEY)
  ↓
selected Claude model
  ↓
Anthropic / Claude Code
```

If `JEV_API_KEY` is unavailable, the adapter may start Claude Code in normal non-routed mode, but it must clearly report that JEV automatic routing is disabled.

## OpenCode integration

The OpenCode adapter must follow the same authentication contract:

1. Detect/launch the real OpenCode runtime.
2. Load `JEV_API_KEY` from the shared configuration layer.
3. Normalize the fresh user turn into the common `RoutingRequest`.
4. Call the JEV API.
5. Resolve the selected model against OpenCode's configured model/provider catalog.
6. Forward the request through OpenCode without breaking its native tools, sessions, permissions, or agent loop.

Conceptual flow:

```text
OpenCode
  ↓
JEV OpenCode Adapter
  ↓
JEV API (JEV_API_KEY)
  ↓
Model Resolver
  ↓
OpenCode model/provider
```

## Other agent integrations

Every future adapter must implement the same contract:

```text
Agent Adapter
    │
    ├── detect / launch
    ├── normalize request
    ├── authenticate JEV through shared JEV client
    ├── call JEV routing API
    ├── resolve returned model
    ├── apply model in native agent format
    └── preserve native execution behavior
```

Adapters must **not** implement their own JEV authentication logic. They should depend on the shared JEV client and configuration modules.

## Integration status must be explicit

The CLI should distinguish:

```text
JEV_API_KEY present
  → JEV routing enabled

JEV_API_KEY missing
  → JEV routing disabled / passthrough mode
```

Do not claim that an agent is "JEV routed" when the API key is missing or the last routing request failed.

---

# 2. Golden Rules

These rules apply to every change in the repository.

## Rule 1 — Never put agent-specific logic in the routing core

Do not write code like:

```python
if agent == "claude":
    ...
elif agent == "codex":
    ...
```

inside the core routing engine.

Agent-specific behavior belongs under:

```text
adapters/
```

The core should work with normalized interfaces.

---

## Rule 2 — Separate agent, router, and provider

Treat these as different layers:

```text
Agent
    owns:
    - tools
    - agent loop
    - permissions
    - sessions
    - UX

Router
    owns:
    - request normalization
    - routing decision
    - policy
    - model selection
    - state/pinning

Provider
    owns:
    - model API
    - authentication
    - request/response transport
```

Do not collapse all three concerns into one module.

---

## Rule 3 — Route fresh user turns, not every tool call

A coding agent may make many requests for one user instruction.

Example:

```text
User request
   ↓
Model call
   ↓
Tool call
   ↓
Tool result
   ↓
Model continuation
   ↓
Tool call
   ↓
Tool result
   ↓
Final answer
```

The router should normally make **one JEV routing decision for that turn** and pin the selected model for the entire agent/tool loop.

Never repeatedly ask JEV merely because the agent made another tool call.

---

## Rule 4 — Human/model overrides are explicit

When the developer explicitly chooses a concrete model, automatic routing must not silently override that choice unless the user explicitly opted into automatic routing.

Automatic mode:

```text
JEV → policy → model
```

Manual mode:

```text
user → chosen model
```

Manual intent takes precedence.

---

## Rule 5 — Fail open

JEV is an optimization layer, not a dependency that should prevent coding.

If any of the following fail:

- JEV API
- network request
- routing timeout
- malformed JEV response
- model catalog lookup
- adapter-specific routing hook
- policy evaluation

then the agent must continue using a safe fallback whenever possible.

Preferred fallback chain:

```text
JEV decision
    ↓ failure
Current model
    ↓ unavailable
Agent default model
    ↓ unavailable
Configured fallback model
    ↓ unavailable
Clear error
```

Never make a routing outage silently destroy the coding session.

---

## Rule 6 — Do not leak prompts or secrets in logs

The router may process highly sensitive codebase context.

Never log by default:

- API keys
- authorization headers
- cookies
- full prompts
- full tool definitions
- repository secrets
- raw source files
- complete model responses

Debug dumps must be explicitly opt-in.

Use redaction before logging structured request data.

---

## Rule 7 — Preserve native agent behavior

Whenever possible, the router should preserve:

- streaming
- tool calls
- permissions
- authentication
- MCP behavior
- sessions
- resume
- model selection UX
- agent-specific commands
- provider-native error semantics

Do not redesign an agent's UX unnecessarily just to implement routing.

---

# 3. Target Architecture

The repository should converge toward a structure similar to:

```text
jev_model_router/
│
├── agents/
│   ├── base/
│   │   ├── adapter.py
│   │   ├── capabilities.py
│   │   └── models.py
│   │
│   ├── claude_code/
│   ├── codex/
│   ├── opencode/
│   ├── deepagents/
│   ├── hermes/
│   └── custom/
│
├── core/
│   ├── router.py
│   ├── policy.py
│   ├── decision.py
│   ├── context.py
│   ├── session.py
│   ├── turn.py
│   └── errors.py
│
├── models/
│   ├── registry.py
│   ├── resolver.py
│   ├── capabilities.py
│   └── catalog.py
│
├── providers/
│   ├── anthropic/
│   ├── openai/
│   ├── google/
│   ├── groq/
│   ├── openrouter/
│   ├── azure/
│   └── compatible/
│
├── transport/
│   ├── proxy.py
│   ├── forwarding.py
│   └── streaming.py
│
├── observability/
│   ├── logging.py
│   ├── metrics.py
│   ├── trace.py
│   └── explain.py
│
├── cli/
│   ├── main.py
│   └── commands/
│
├── config/
│   ├── loader.py
│   └── schema.py
│
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── adapters/
│   ├── providers/
│   └── fixtures/
│
├── docs/
│
├── ARCHITECTURE.md
├── AGENTS.md
├── README.md
└── pyproject.toml
```

The exact directory layout may evolve, but the architectural separation must remain.

---

# 4. Core Data Contracts

All agents should normalize into a common internal request representation.

A conceptual request is:

```python
RoutingRequest(
    agent="claude-code",
    session_id="...",
    turn_id="...",
    prompt="...",
    messages=[...],
    tools=[...],
    current_model="...",
    available_models=[...],
    context_tokens=..., 
    metadata={...},
)
```

The exact implementation can use dataclasses, Pydantic models, TypedDicts, or another strongly typed approach, but the contract must remain explicit.

## Required routing fields

At minimum, the normalized request should be able to represent:

- agent identity
- session identity
- turn identity
- user prompt or turn input
- current model
- candidate models
- context size estimate
- tool complexity information
- relevant capability requirements
- explicit user model override
- routing mode

Optional fields should be nullable rather than invented from unreliable data.

---

# 5. JEV Decision Contract

The JEV result should be normalized before policy evaluation.

Conceptually:

```python
JEVDecision(
    selected_model="...",
    confidence=0.93,
    task_complexity=0.8,
    reasoning_required=0.9,
    tool_complexity=0.7,
    explanation="...",
)
```

Do not allow provider-specific or agent-specific response formats to spread through the codebase.

Normalize external responses at the boundary.

---

# 6. Policy Layer

JEV should not directly mutate agent requests.

The sequence must be:

```text
JEV output
   ↓
Policy evaluation
   ↓
Policy decision
   ↓
Concrete model resolution
```

The policy layer should handle at least:

### Explicit override

```text
User explicitly requested model X
→ honor X
```

### JEV unavailable

```text
Keep current model
```

### Low confidence

Potential policy:

```text
Low confidence + downgrade
→ refuse downgrade

Low confidence + aggressive upgrade
→ optionally cap upgrade
```

Exact thresholds must be configurable and tested rather than scattered through the code.

### Model unavailable

Never select a model that the selected agent/provider cannot actually use.

### Context-sensitive downgrade protection

Switching models may force prompt/context reprocessing or reduce cache reuse.

The policy may therefore refuse a downgrade when the context is sufficiently large.

This behavior must be explicit and documented.

---

# 7. Model Registry

Do not hard-code model routing decisions directly into agent adapters.

The model registry should describe models using normalized capabilities.

Example:

```yaml
models:
  claude-sonnet:
    provider: anthropic
    capabilities:
      coding: 9
      reasoning: 8
      tool_use: 9
      context: 9
      speed: 9
      cost_efficiency: 7

  claude-opus:
    provider: anthropic
    capabilities:
      coding: 10
      reasoning: 10
      tool_use: 10
      context: 10
      speed: 5
      cost_efficiency: 4
```

The registry should eventually support:

- provider
- model identifier
- aliases
- capability metadata
- context window
- tool support
- vision support
- structured output support
- reasoning support
- latency class
- cost class
- availability
- agent compatibility

Never assume two models from different providers have identical API semantics merely because both are chat models.

---

# 8. Model Resolution

JEV should reason about the required capability; the model resolver should select a concrete model.

Example:

```text
JEV:
    required profile = strong reasoning + strong coding

Resolver:
    candidates = models supported by this agent
    ↓
    filter unavailable models
    ↓
    filter incompatible models
    ↓
    apply policy
    ↓
    choose concrete model
```

This makes the project portable across agents and providers.

---

# 9. Agent Adapter Contract

Every coding agent integration should implement the same conceptual adapter API.

Example:

```python
class AgentAdapter(Protocol):
    name: str

    def detect(self) -> bool:
        ...

    def capabilities(self) -> AgentCapabilities:
        ...

    def parse_request(self, request) -> RoutingRequest | None:
        ...

    def is_fresh_turn(self, request) -> bool:
        ...

    def is_manual_model_selection(self, request) -> bool:
        ...

    def apply_model(self, request, model):
        ...

    def forward(self, request):
        ...
```

The concrete method names may change, but every adapter must solve the same conceptual problems.

---

# 10. Adapter Responsibilities

An adapter is responsible for understanding one agent's protocol.

For example:

```text
agents/claude_code/
    request_parser
    model_catalog
    turn_detection
    transport
    model_rewriter
```

The adapter may know:

- exact request schema
- streaming protocol
- model picker behavior
- custom endpoint configuration
- session metadata
- request IDs
- agent-specific headers
- agent-specific auxiliary calls

The adapter must **not** decide whether a task is easy or hard.

That is core routing policy.

---

# 11. Provider Layer

Providers represent model backends.

Examples:

```text
providers/anthropic
providers/openai
providers/google
providers/groq
providers/openrouter
providers/azure
providers/compatible
```

Provider code owns:

- endpoint URLs
- authentication conventions
- request transformation
- response transformation
- streaming details
- provider-specific error handling

Providers must not contain JEV routing policy.

---

# 12. Agent ↔ Provider Compatibility

An important distinction:

```text
Agent support != Provider support
```

For example, an agent may natively support only some providers/models.

The resolver must calculate:

```text
Available Models
    ∩
Agent-Compatible Models
    ∩
Provider-Compatible Models
    ∩
Policy-Allowed Models
```

Only the resulting set is selectable.

---

# 13. Routing Lifecycle

The standard routing lifecycle should look like:

```text
1. Agent generates request
        ↓
2. Adapter intercepts request
        ↓
3. Adapter determines whether it is a fresh turn
        ↓
4. Adapter normalizes request
        ↓
5. Router gathers context
        ↓
6. Router checks explicit user override
        ↓
7. Router asks JEV
        ↓
8. JEV returns normalized decision
        ↓
9. Policy evaluates decision
        ↓
10. Model resolver chooses concrete model
        ↓
11. Session/turn state records selected model
        ↓
12. Adapter rewrites request
        ↓
13. Request is forwarded
        ↓
14. All subsequent tool-loop requests remain pinned
```

---

# 14. Turn State

Model decisions should be scoped to a turn/session.

Conceptually:

```python
TurnState(
    session_id="...",
    turn_id="...",
    selected_model="...",
    selected_at=...,
    confidence=...,
    reason="...",
)
```

Do not use a single global `current_model` for the entire process when the agent can run:

- parallel sessions
- sub-agents
- background tasks
- nested agent loops

State should be isolated using stable session/turn identifiers.

---

# 15. Sub-Agents

Sub-agents are a first-class concern.

A coding agent may spawn another agent with different context.

Do not allow sub-agent routing decisions to accidentally overwrite the parent session's model.

Prefer:

```text
Main session A
    ├── turn 1 → model X
    └── sub-agent A1 → model Y

Main session B
    └── turn 1 → model Z
```

State keys must be scoped appropriately.

---

# 16. Fresh Turn Detection

Fresh-turn detection is adapter-specific, but the output is universal:

```text
fresh turn → route
continuation → use pinned model
auxiliary call → usually bypass routing
```

The adapter must carefully distinguish:

- user turns
- tool results
- tool calls
- summaries
- title generation
- telemetry calls
- model catalog requests
- health checks
- background requests

Do not route every request indiscriminately.

---

# 17. Proxy / Transport Layer

The transport layer should be independent of routing policy.

Its job is:

```text
accept request
    ↓
inspect / normalize
    ↓
rewrite model where required
    ↓
forward request
    ↓
stream response back
```

Transport implementations may include:

```text
HTTP reverse proxy
Loopback proxy
OpenAI-compatible proxy
Provider-specific transport
CLI environment wrapper
SDK middleware
```

Choose the least invasive mechanism compatible with each agent.

---

# 18. Streaming Requirements

Streaming is not optional for production-quality agent integration.

The router must avoid buffering an entire model response when the native protocol expects streaming.

Preferred behavior:

```text
Upstream stream
    ↓
minimal inspection / transformation
    ↓
immediate downstream stream
```

If routing metadata must be surfaced to the user, inject it without disrupting the response stream.

---

# 19. Configuration

Configuration should use predictable precedence.

Recommended order:

```text
CLI arguments
    > environment variables
    > project config
    > user config
    > defaults
```

Configuration should cover:

- JEV API credentials
- routing mode
- confidence thresholds
- fallback model
- model registry location
- provider configuration
- debug mode
- telemetry mode
- enabled adapters
- proxy ports
- routing timeouts

Never commit credentials.

---

# 20. CLI Design

The CLI should be easy for developers to understand.

Possible future commands:

```bash
jev-router doctor
jev-router status
jev-router config
jev-router models
jev-router agents
jev-router explain
jev-router run claude
jev-router run codex
jev-router run opencode
```

The CLI should provide useful diagnostics without requiring users to understand internal implementation details.

---

# 21. `doctor` Expectations

A diagnostic command should eventually check:

```text
✓ JEV credentials
✓ agent installation
✓ agent detection
✓ provider connectivity
✓ model catalog
✓ adapter availability
✓ local proxy binding
✓ configuration validity
```

Failures should include a concrete remediation message.

---

# 22. Explainability

Every automatic routing decision should have an inspectable representation.

Example:

```text
JEV Model Router
──────────────────────────────
Agent:              Claude Code
Task:               repository-wide auth migration
Current model:      balanced
Selected model:     strong
Confidence:         0.93

Signals
  Task complexity       0.90
  Reasoning required    0.94
  Tool complexity       0.81
  Context size          0.42

Policy
  Upgrade allowed       yes
  Model available       yes
  Context downgrade     not applicable

Decision
  route → strong
```

The displayed explanation should be derived from the stored routing decision where possible, rather than calling JEV again just to explain the same decision.

---

# 23. Observability

Use structured events internally.

Conceptual event:

```json
{
  "event": "routing.decision",
  "agent": "codex",
  "session_id": "redacted",
  "turn_id": "redacted",
  "current_model": "balanced",
  "selected_model": "strong",
  "confidence": 0.93,
  "reason": "jev",
  "latency_ms": 412
}
```

Never log sensitive prompt content by default.

Recommended metrics:

- routing decision latency
- JEV success rate
- JEV timeout rate
- fallback rate
- override rate
- model-switch rate
- per-agent routing count
- per-model selection count
- proxy error rate
- streaming interruption rate

---

# 24. Error Handling

Errors should be typed and actionable.

Suggested categories:

```text
ConfigurationError
AuthenticationError
AgentDetectionError
AdapterError
RoutingError
PolicyError
ModelResolutionError
ProviderError
TransportError
StreamingError
```

Do not catch all exceptions and silently continue without recording why the fallback occurred.

Fail open does not mean fail silently.

---

# 25. Security

Security rules are mandatory.

## Never expose

- API keys
- authorization headers
- cookies
- refresh tokens
- filesystem credentials
- SSH credentials
- cloud credentials
- repository secrets

## Treat prompts as sensitive

Prompts may contain proprietary code, internal architecture, credentials, or business information.

Only send what is required for routing.

## Debug dumps

If a request-dump mode exists:

- make it opt-in
- clearly warn the user
- redact known secret fields
- write restrictive file permissions
- document the storage location
- make cleanup possible

---

# 26. Privacy Boundary

The router should send JEV only the minimum routing information necessary.

Prefer:

```text
prompt
context size
available model IDs
current model
tool complexity metadata
```

over:

```text
entire repository
full filesystem
all tool outputs
all environment variables
full authentication context
```

If additional context materially improves routing, make that expansion explicit and configurable.

---

# 27. Testing Strategy

Every non-trivial change requires tests.

## Unit tests

Test pure logic first:

- policy
- confidence thresholds
- explicit overrides
- model compatibility
- registry filtering
- model resolution
- turn detection helpers
- state isolation
- fallback selection

## Adapter tests

Each agent adapter should have fixture-driven tests for:

- basic request
- fresh user turn
- tool continuation
- manual model choice
- auxiliary request
- streaming response
- malformed request
- unavailable model

## Integration tests

Test full flows:

```text
agent request
 → adapter
 → router
 → mocked JEV
 → policy
 → resolver
 → rewritten request
```

## Live tests

Live JEV/provider tests must be explicitly marked and never required for ordinary CI.

---

# 28. Regression Fixtures

Whenever an upstream coding agent changes its request schema, add the captured sanitized request/response as a fixture.

Fixtures should:

- remove secrets
- remove proprietary code where possible
- preserve protocol structure
- include the agent version
- include expected routing behavior

Upstream protocol changes are expected. Tests are how we keep integrations stable.

---

# 29. Dependency Rules

Keep dependencies minimal.

Before adding a dependency, ask:

1. Is it necessary?
2. Can the standard library solve it?
3. Does it increase startup latency?
4. Does it complicate packaging?
5. Does it create security or licensing concerns?
6. Is it maintained?

Do not add a framework merely for convenience.

---

# 30. Performance Rules

Routing runs on a hot path.

Optimize for:

```text
low startup overhead
low routing latency
minimal request copying
stream preservation
bounded memory
minimal duplicate serialization
```

Use timeouts around external routing calls.

Never allow a stuck JEV request to hang an otherwise healthy coding session indefinitely.

Recommended behavior:

```text
JEV request
    ↓
short timeout
    ↓ timeout
fallback immediately
```

Retry only when the retry budget is compatible with interactive latency.

---

# 31. Caching and State

Be conservative with routing caches.

The router should not accidentally reuse a routing decision between unrelated tasks.

Safe dimensions for state may include:

```text
agent
session
turn
current model
context state
```

Avoid simplistic global caches such as:

```text
"all prompts like X use model Y"
```

unless the behavior is explicitly designed and tested.

---

# 32. Model Catalog Handling

Model catalogs may change over time.

Do not assume model IDs are static forever.

Adapters should prefer discovering the actual models available to an authenticated agent/provider where practical.

When catalog data is unavailable, use configured fallbacks.

Never fabricate model IDs.

---

# 33. Upstream Compatibility

Coding-agent protocols are often undocumented, unstable, or version-dependent.

Treat request formats as external contracts that can change.

For every adapter:

```text
capture
→ normalize
→ test
→ document
```

Record tested versions in adapter documentation.

When an upstream release changes request structure, isolate the compatibility patch inside that adapter.

Do not leak compatibility hacks into the core router.

---

# 34. Adding a New Coding Agent

When adding an agent such as `foo-agent`:

### Step 1 — Research its request flow

Determine:

- request protocol
- response protocol
- streaming
- model selection
- session identifiers
- tool calls
- sub-agent behavior
- authentication
- custom endpoint support

### Step 2 — Create adapter

Add:

```text
agents/foo_agent/
```

### Step 3 — Implement normalization

Convert the native request into `RoutingRequest`.

### Step 4 — Implement fresh-turn detection

Return whether JEV should be called.

### Step 5 — Implement model application

Apply the resolved model without changing unrelated agent behavior.

### Step 6 — Add fixtures

Add representative request/response fixtures.

### Step 7 — Add tests

Cover manual selection, automatic routing, tool loops, streaming, and failure paths.

### Step 8 — Document compatibility

Add the supported agent/version matrix.

Do not modify the core to understand `foo-agent`.

---

# 35. Adding a New Provider

When adding a provider:

1. Create provider implementation.
2. Define authentication behavior.
3. Define model catalog behavior.
4. Normalize request/response semantics.
5. Implement streaming.
6. Add compatibility tests.
7. Register models in the model registry.
8. Document limitations.

The provider must not know why the router selected the model.

---

# 36. Adding a New Routing Signal

Examples:

- repository size
- context size
- tool count
- reasoning intensity
- code-language complexity
- estimated change blast radius
- latency requirement
- user cost preference

Implement signals in a way that does not couple them to a specific agent.

Prefer:

```text
raw agent request
    ↓
normalized context
    ↓
signal extraction
```

rather than reading protocol-specific fields throughout the policy engine.

---

# 37. Repository-Wide Coding Style

Prefer:

- small modules
- clear interfaces
- pure functions for policy logic
- type hints
- explicit error types
- deterministic tests
- descriptive names
- comments explaining *why*, not obvious *what*

Avoid:

- god classes
- global mutable state
- hidden side effects
- provider-specific branches in core code
- magic constants
- duplicated model maps
- swallowing exceptions
- unnecessary abstraction layers

---

# 38. Change Workflow for Coding Agents

Before editing:

```text
1. Read AGENTS.md
2. Read relevant architecture section in ARCHITECTURE.md
3. Inspect the existing implementation
4. Identify the correct layer
5. Make the smallest coherent change
```

After editing:

```text
1. Format/lint
2. Type-check if configured
3. Run targeted tests
4. Run relevant integration tests
5. Run the full test suite when practical
6. Review the diff
7. Confirm no secrets/debug dumps were added
```

Do not rewrite unrelated code.

---

# 39. Architecture Decision Test

Before putting code into a module, ask:

### Is it about an agent's protocol?

→ `agents/`

### Is it about routing logic?

→ `core/`

### Is it about model metadata or availability?

→ `models/`

### Is it about an upstream model API?

→ `providers/`

### Is it about HTTP/stream transport?

→ `transport/`

### Is it about logs/metrics/explanations?

→ `observability/`

### Is it about CLI behavior?

→ `cli/`

If none fit, stop and reconsider the architecture before creating another generic utility module.

---

# 40. Definition of Done

A feature is not complete merely because it works locally.

For a production-quality change, the coding agent should verify:

```text
[ ] Correct architectural layer
[ ] No agent-specific logic leaked into core
[ ] No provider-specific logic leaked into policy
[ ] Explicit model overrides preserved
[ ] Fresh-turn routing preserved
[ ] Tool-loop pinning preserved
[ ] Failure fallback implemented
[ ] Secrets excluded from logs
[ ] Tests added/updated
[ ] Existing tests pass
[ ] Streaming preserved where applicable
[ ] Documentation updated when behavior changed
```

---

# 41. Priority Order

When requirements conflict, use this priority order:

```text
1. Safety and security
2. Preserve user intent / explicit model choice
3. Preserve native agent behavior
4. Correctness of routing
5. Availability / graceful fallback
6. Performance / latency
7. Cost optimization
8. Convenience / cosmetic improvements
```

The router should never optimize cost at the expense of an explicit user decision or a broken coding session.

---

# 42. Preferred Development Philosophy

JEV Model Router should be built as **infrastructure**, not as a collection of hacks for individual coding agents.

The long-term mental model is:

```text
                  ┌────────────────────┐
                  │    Coding Agents   │
                  ├────────────────────┤
                  │ Claude Code        │
                  │ Codex              │
                  │ OpenCode           │
                  │ DeepAgents         │
                  │ Hermes             │
                  │ Custom Agents      │
                  └─────────┬──────────┘
                            │
                            ▼
                ┌────────────────────────┐
                │    JEV Model Router    │
                │                        │
                │  normalize             │
                │  analyze               │
                │  route                 │
                │  policy                │
                │  resolve               │
                │  pin                   │
                │  explain               │
                └───────────┬────────────┘
                            │
             ┌──────────────┼──────────────┐
             ▼              ▼              ▼
        Anthropic        OpenAI         Other Providers
```

The most important property of the project is not the number of supported agents.

It is that **adding the next agent does not require rewriting the routing engine**.

---

# 43. Final Instruction to Coding Agents

When modifying this repository:

> **Preserve the separation between agent integration, routing policy, model resolution, and provider transport.**
>
> **Build reusable abstractions before adding agent-specific behavior.**
>
> **Route fresh turns, pin the decision through tool loops, honor explicit user choices, fail open, protect secrets, and test every protocol assumption.**

When uncertain about where a change belongs, prefer the narrowest layer that owns the behavior and keep the core protocol-independent.
