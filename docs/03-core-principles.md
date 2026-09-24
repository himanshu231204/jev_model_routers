# Core Principles and Rules

> Source: `ARCHITECTURE.md` (§4, §100, §106) — verbatim split, do not edit here; propose changes against the source section.

> Back to index: [docs/README.md](./README.md)

---

# 4. Core Architectural Principle

The most important contract is:

```text
AgentRequest
    ↓
NormalizedRequest
    ↓
JEVDecision
    ↓
PolicyDecision
    ↓
ModelResolution
    ↓
ProviderRequest
    ↓
AgentResponse
```

This creates a hard boundary between integration code and routing logic.

A simplified type model:

```text
AgentRequest
{
    agent
    session
    turn
    messages
    tools
    current_model
    available_models
    metadata
}

        ↓ normalize

RoutingContext
{
    task
    context
    tools
    session
    current_model
    candidates
}

        ↓ JEV

JEVDecision
{
    requested_capability
    selected_model_or_tier
    confidence
    scores
    explanation
}

        ↓ policy

RoutingDecision
{
    final_model
    reason
    changed
    fallback
    pinned_until
}

        ↓ adapter

Agent-native request
```

---

---

# 100. Architectural Rules — Keep These Strict

These should become project-level engineering rules.

## Rule 1 — Core never imports an agent adapter

```text
core → contracts
core → providers
core → state

NOT

core → claude
core → codex
```

## Rule 2 — Adapter never owns routing policy

Adapters parse and rewrite requests.

They do not decide which model is "better".

## Rule 3 — JEV never becomes the runtime state manager

JEV makes a recommendation.

JEV is not the source of truth for:

```text
sessions
turns
manual overrides
provider availability
agent state
```

## Rule 4 — One routing decision per fresh turn

Do not re-route every tool call.

## Rule 5 — Explicit user choice wins

Automation should optimize the workflow, not override deliberate model selection.

## Rule 6 — Fail open

Routing failure must not normally stop coding.

## Rule 7 — No protocol leakage

Agent-specific request formats remain inside adapters.

## Rule 8 — Capability first, vendor second

The core should think:

```text
strong reasoning
```

not:

```text
use Claude Opus because Claude is installed
```

## Rule 9 — Preserve native behavior

The router should be as invisible as possible during normal coding.

## Rule 10 — Minimize sensitive data

Only send what is needed to make a routing decision.

---

---

# 106. Final Principle

```text
                    JEV MODEL ROUTER

          "Decide the model. Don't become the agent."

        Agent                 Router                 Model
          │                     │                      │
          │  What is the task?  │                      │
          ├────────────────────>                      │
          │                     │                      │
          │                     │ Ask JEV              │
          │                     ├───────────────>      │
          │                     │<───────────────      │
          │                     │                      │
          │                     │ Which model?         │
          │                     │                      │
          │<────────────────────┤                      │
          │                     │                      │
          │───────────────────────────────────────────>│
          │                     │                      │
          │<───────────────────────────────────────────│

                    Keep the agent native.
                    Keep routing centralized.
                    Keep models replaceable.
```
