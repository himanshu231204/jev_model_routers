# JEV Model Router

> An agent-agnostic model routing layer for AI coding agents.

JEV Model Router sits between coding agents and the models they use.

Instead of forcing every coding task onto one model, it uses the **JEV API** to decide which available model is appropriate for the current task, then lets the connected coding agent continue normally.

The goal is simple:

```text
                    Your Coding Task
                           │
                           ▼
                ┌────────────────────┐
                │   Coding Agent     │
                │                    │
                │ Claude Code        │
                │ Codex              │
                │ OpenCode           │
                │ DeepAgents         │
                │ Hermes / others    │
                └─────────┬──────────┘
                          │
                          ▼
                ┌────────────────────┐
                │  JEV Model Router  │
                │                    │
                │ Normalize request  │
                │ Ask JEV             │
                │ Apply policy        │
                │ Resolve model       │
                └─────────┬──────────┘
                          │
                          ▼
                       JEV API
                          │
                          ▼
                  Routing decision
                          │
                          ▼
                ┌────────────────────┐
                │   Selected Model   │
                │                    │
                │ Fast / Balanced    │
                │ Strong / Long      │
                └─────────┬──────────┘
                          │
                          ▼
                    Task execution
```

## Why JEV Model Router?

Coding agents increasingly support multiple models, providers, and execution modes. But different coding tasks do not need the same level of reasoning.

A simple README edit may not need the strongest model.

A repository-wide architectural migration might.

JEV Model Router is designed to make that decision **per user turn**, while keeping the original coding agent, tools, sessions, permissions, and provider integration intact.

### Example

```text
Task 1:
"Rename this variable and update the references."

                 ↓ JEV

                FAST
                 ↓
             cheap model


Task 2:
"Find the root cause of this intermittent authentication
failure across the API, database, middleware and token flow."

                 ↓ JEV

               STRONG
                 ↓
           reasoning model
```

The user still works with the same coding agent.

Only the model selection changes.

---

# Core Principles

JEV Model Router is built around a few important principles.

### 1. Agent-agnostic

The routing core should not be tightly coupled to Claude Code, Codex, OpenCode, DeepAgents, Hermes, or any single coding agent.

Each agent is integrated through an adapter.

```text
Claude Code ──┐
Codex ────────┤
OpenCode ─────┤
DeepAgents ───┤──► Agent Adapter ──► JEV Router Core
Hermes ───────┤
Other agents ─┘
```

### 2. JEV-powered routing

**JEV is the routing authority.**

The router sends the normalized coding request to the JEV API and uses the returned recommendation as the primary routing signal.

Authentication is provided through:

```bash
JEV_API_KEY=your_key
```

The API key must never be hard-coded, committed, or printed in logs.

### 3. Policy before execution

JEV makes a recommendation, but the router still applies local policy.

```text
JEV Recommendation
        │
        ▼
   Policy Engine
        │
        ├── confidence checks
        ├── explicit user overrides
        ├── model availability
        ├── context/cache constraints
        ├── safety/fallback rules
        │
        ▼
   Final Model Decision
```

This keeps routing deterministic and reviewable.

### 4. One decision per user turn

The router should make a routing decision when a **new user turn** starts.

Tool-loop continuations reuse the selected model.

```text
User Turn
   │
   ▼
JEV decision
   │
   ▼
Model pinned for turn
   ├── tool call
   ├── tool call
   ├── tool result
   ├── tool call
   └── continuation
```

This avoids model switching in the middle of a single task.

### 5. Fail open

Routing should optimize the coding experience, not become a single point of failure.

If JEV is unavailable, times out, returns an invalid response, or the key is missing, the coding agent should continue using the configured/default/current model whenever possible.

```text
JEV unavailable
     │
     ▼
Fallback policy
     │
     ▼
Continue coding
```

---

# Architecture

The project is organized into a shared routing core plus agent-specific adapters.

```text
jev_model_router/
│
├── cli/
│   └── User-facing commands
│
├── core/
│   ├── router
│   ├── policy
│   ├── state
│   └── model resolution
│
├── jev/
│   └── JEV API client
│
├── adapters/
│   ├── claude_code/
│   ├── codex/
│   ├── opencode/
│   ├── deepagents/
│   └── hermes/
│
├── proxy/
│   └── HTTP/API interception where required
│
├── models/
│   ├── registry
│   ├── capabilities
│   └── provider mappings
│
├── observability/
│   ├── logs
│   ├── metrics
│   └── routing explanations
│
├── config/
│   └── runtime configuration
│
└── tests/
```

The main flow is:

```text
Agent Request
     │
     ▼
Agent Adapter
     │
     ▼
Normalized Request
     │
     ▼
JEV Client
     │
     │ JEV_API_KEY
     ▼
JEV API
     │
     ▼
JEV Recommendation
     │
     ▼
Policy Engine
     │
     ▼
Model Resolver
     │
     ▼
Agent-specific Model Request
     │
     ▼
Provider / Model
```

---

# Request Lifecycle

## 1. The coding agent creates a request

For example:

```text
"Refactor the authentication middleware and update the tests."
```

The request may contain:

- prompt text
- current model
- available models
- session information
- context size
- tool definitions
- agent metadata

Different agents expose these details differently.

---

## 2. The adapter normalizes the request

Every adapter converts its native request into a common representation.

Conceptually:

```python
NormalizedRequest(
    agent="claude-code",
    session_id="...",
    turn_id="...",
    prompt="Refactor authentication middleware...",
    current_model="claude-sonnet",
    available_models=[...],
    context_tokens=42000,
    tools=[...],
)
```

The core router operates on this normalized request rather than on agent-specific wire formats.

---

## 3. JEV evaluates the task

The JEV client sends the relevant routing information to the JEV API.

The router can use information such as:

```text
Task complexity
Reasoning required
Tool complexity
Context size
Available models
Current model
```

A response may conceptually look like:

```json
{
  "model": "strong-model",
  "confidence": 0.94
}
```

The exact JEV response schema is owned by the JEV API integration layer.

---

## 4. Policy validates the recommendation

The policy layer converts the JEV answer into a final decision.

Example:

```text
JEV:
downgrade to fast

Context:
very large

Policy:
keep current model
```

Another example:

```text
JEV:
strong model

Confidence:
very low

Policy:
apply configured confidence rules
```

The policy layer is deliberately separate from the JEV client.

---

## 5. Model Resolver selects the concrete model

The router should separate an abstract routing decision from a concrete provider model.

For example:

```text
strong
  │
  ├── Anthropic → configured strong model
  ├── OpenAI    → configured strong model
  ├── Google    → configured strong model
  └── OpenRouter → configured strong model
```

This allows model IDs to change without rewriting the routing architecture.

---

## 6. The adapter applies the result

The adapter converts the final decision back into the native format required by the coding agent.

The agent then continues as usual.

---

# Agent Integrations

JEV Model Router is designed to support multiple coding agents through adapters.

| Agent | Integration concept |
|---|---|
| Claude Code | adapter / proxy |
| OpenAI Codex | adapter / proxy |
| OpenCode | adapter / provider integration |
| DeepAgents | SDK / middleware integration |
| Hermes | adapter / provider integration |
| Future agents | new adapter |

The exact integration mechanism can differ by agent.

The core routing engine should remain unchanged.

---

# Integration Modes

Different coding agents expose different extension points. The project therefore supports multiple integration patterns.

## Wrapper

A wrapper launches the real agent with JEV routing enabled.

```text
jev wrapper
     │
     ▼
coding agent
     │
     ▼
JEV router
```

Useful when the agent can be configured through startup arguments or environment variables.

## Reverse Proxy

A local proxy sits between the agent and provider API.

```text
Coding Agent
     │
     ▼
localhost proxy
     │
     ├── JEV decision
     │
     ▼
Provider API
```

This is useful when an agent supports a configurable base URL or provider endpoint.

## SDK Middleware

For SDK-based agents, routing can happen directly around the model invocation.

```text
Agent
 │
 ▼
JEV middleware
 │
 ├── ask JEV
 ├── resolve model
 │
 ▼
Model
```

---

# JEV API Authentication

JEV routing requires a JEV API key.

Set:

```bash
export JEV_API_KEY="your_j ev_api_key"
```

On Windows PowerShell:

```powershell
$env:JEV_API_KEY="your_jev_api_key"
```

Do not commit secrets.

Recommended:

```text
.env
~/.jev-router.env
OS secret manager
CI/CD secret store
```

Never:

```text
source code
README
git history
logs
debug dumps
```

The shared JEV client should be the only component responsible for JEV authentication.

Adapters should not each implement their own JEV authentication logic.

---

# Configuration

The router should keep configuration separate from routing logic.

Typical configuration includes:

```yaml
routing:
  enabled: true
  confidence_threshold: 0.30
  route_per_turn: true
  fail_open: true

models:
  fast: ...
  balanced: ...
  strong: ...
  long: ...

providers:
  anthropic: ...
  openai: ...
  google: ...
```

The exact configuration schema should evolve with the implementation.

---

# Explicit User Overrides

Automatic routing should never override an explicit model choice.

Conceptually:

```text
User explicitly selects model
          │
          ▼
    Manual override
          │
          ▼
    Skip automatic routing
```

For example, if an integration supports:

```text
"use Opus"
```

or the user manually selects a concrete model in the agent's UI, that explicit choice should take precedence over automatic routing where the adapter can reliably detect it.

---

# Session and Turn State

The router must distinguish:

```text
Session
  └── Conversation
        └── User Turn
              └── Tool Loop
```

A routing decision belongs to a turn.

Example:

```text
Session A
│
├── Turn 1 → Fast
│   ├── tool call
│   ├── tool call
│   └── done
│
├── Turn 2 → Balanced
│   ├── tool call
│   └── done
│
└── Turn 3 → Strong
    ├── tool call
    ├── tool call
    └── done
```

The state layer should prevent one conversation or sub-agent from accidentally inheriting another conversation's routing decision.

---

# Model Registry

The model registry is responsible for describing models and their capabilities.

A model entry may include:

```yaml
id: claude-sonnet
provider: anthropic

capabilities:
  coding: 9
  reasoning: 8
  tool_use: 9
  context: 8
  speed: 8
  cost: 5
```

The registry allows the router to distinguish:

```text
routing tier
    ≠
concrete model ID
```

This makes the system easier to maintain as model catalogs evolve.

---

# Safety and Reliability

JEV Model Router should follow these runtime rules.

### Never block coding because routing failed

```text
JEV timeout
JEV 5xx
invalid response
missing API key
network error
```

should normally resolve to a safe fallback.

### Never leak secrets

Do not include:

```text
JEV_API_KEY
provider API keys
authorization headers
```

in logs, traces, routing explanations, or debug dumps.

### Never route every tool call independently

Routing is per user turn, not per HTTP request.

### Never silently replace explicit user choices

Manual selections must remain authoritative.

### Preserve native agent behavior

Adapters should avoid changing:

- permissions
- sessions
- tool behavior
- authentication
- normal CLI commands
- provider-specific features

unless required for the integration itself.

---

# Observability

The router should make routing decisions explainable without exposing secrets or full sensitive prompts.

A useful event might contain:

```json
{
  "agent": "claude-code",
  "session_id": "...",
  "turn_id": "...",
  "selected_model": "...",
  "reason": "jev",
  "confidence": 0.94,
  "latency_ms": 420
}
```

A local explanation command can eventually show:

```text
JEV Model Router

Task complexity     High
Reasoning required  Very high
Tool complexity     High
Context size        Medium

Recommendation:
Strong

Confidence:
94%

Final model:
<resolved model>

Reason:
JEV recommendation accepted
```

Sensitive prompt content should be minimized or omitted from logs by default.

---

# Testing Strategy

The repository should have multiple layers of tests.

## Unit Tests

Test:

- policy decisions
- confidence handling
- explicit overrides
- model resolution
- state isolation
- fallback logic
- normalization

## Adapter Tests

Each adapter should test:

- request detection
- prompt extraction
- session/turn identification
- model replacement
- passthrough behavior
- error handling

## JEV Client Tests

Normal tests should mock the JEV API.

Live JEV tests should be opt-in and require:

```bash
JEV_API_KEY
```

## Integration Tests

Test the full flow:

```text
Agent
  ↓
Adapter
  ↓
Router
  ↓
JEV mock/live
  ↓
Policy
  ↓
Model resolver
  ↓
Provider request
```

---

# Development Philosophy

Keep the architecture modular.

A new agent should ideally require:

```text
1. Create adapter
2. Normalize native request
3. Implement model application
4. Add adapter tests
```

It should **not** require rewriting:

- JEV authentication
- policy engine
- routing state
- model registry
- observability
- core router

That is the main architectural boundary of the project.

---

# Roadmap

## Phase 1 — Core Router

- [ ] JEV API client
- [ ] normalized request schema
- [ ] normalized routing decision
- [ ] policy engine
- [ ] model registry
- [ ] session/turn state
- [ ] fallback behavior
- [ ] unit tests

## Phase 2 — First Agent Adapters

- [ ] Claude Code
- [ ] Codex
- [ ] OpenCode

## Phase 3 — SDK-Based Agents

- [ ] DeepAgents
- [ ] Hermes
- [ ] generic SDK adapter interface

## Phase 4 — Developer Experience

- [ ] CLI
- [ ] configuration file
- [ ] routing explanation
- [ ] structured logs
- [ ] debug mode
- [ ] model catalog discovery

## Phase 5 — Advanced Routing

- [ ] richer model capabilities
- [ ] context-aware routing
- [ ] cache-aware routing
- [ ] cost-aware routing
- [ ] latency-aware routing
- [ ] routing analytics
- [ ] adapter/plugin ecosystem

---

# Project Goal

The long-term goal is to make model routing a reusable infrastructure layer for coding agents.

```text
                  ANY CODING AGENT
                         │
                         ▼
                ┌─────────────────┐
                │ JEV Model Router│
                └────────┬────────┘
                         │
                         ▼
                    JEV API
                         │
                         ▼
              Best-fit available model
```

You should be able to change the coding agent without rebuilding the router.

You should be able to change the provider without rebuilding the routing core.

You should be able to add a new model without rewriting agent integrations.

That is the central design goal of **JEV Model Router**.

---

# License

Add the project's chosen open-source license here.

---

# Contributing

Contributions should preserve the core architecture:

> **Agents adapt to the router. The router should not become agent-specific.**

When adding a new integration, prefer a new adapter over adding agent-specific branches to the routing core.

See `ARCHITECTURE.md` for the complete architecture and `AGENTS.md` for repository development instructions.
