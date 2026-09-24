# Design Goals and Non-Goals

> Source: `ARCHITECTURE.md` (§2, §3) — verbatim split, do not edit here; propose changes against the source section.

> Back to index: [docs/README.md](./README.md)

---

# 2. Design Goals

## 2.1 Primary goals

### Agent agnostic

The router must not assume that Claude Code, Codex, OpenCode, Hermes, or another agent is the primary runtime.

```text
Core router
    │
    ├── Claude adapter
    ├── Codex adapter
    ├── OpenCode adapter
    ├── DeepAgents adapter
    ├── Hermes adapter
    └── Custom adapter SDK
```

### Per-turn intelligent routing

JEV should make a routing decision at the beginning of a **fresh user turn**, not repeatedly for every tool call.

Example:

```text
User turn
   │
   ├── model selected by JEV
   │
   ├── tool call
   ├── tool call
   ├── tool call
   ├── tool result
   └── continuation

All requests above remain pinned to the same routing decision.
```

This avoids model switching in the middle of an agent's reasoning/tool loop.

### Native agent experience

The router should preserve as much of the original agent experience as possible:

- tool execution
- permission systems
- sessions
- resume functionality
- MCP
- streaming
- context handling
- agent-specific commands
- model picker where possible
- existing authentication where possible

### Provider agnostic

JEV should not directly hard-code one provider as the only destination.

The model registry must support:

```text
Anthropic
OpenAI
Google
Groq
OpenRouter
Azure OpenAI
Bedrock
Ollama
LM Studio
Custom OpenAI-compatible endpoints
Native provider APIs
```

### Fail open

Routing must never make the coding agent unusable.

If JEV is unavailable:

```text
JEV failure
   ↓
Policy fallback
   ↓
Current/default model
   ↓
Agent continues
```

### Explicit human override

If the developer explicitly chooses a model, that choice must normally take precedence over automatic routing.

```text
Automatic routing:
    JEV decides

Explicit routing:
    User decides
```

### Explainability

Every routing decision should be explainable locally:

```text
Why was this model selected?

Task complexity:       High
Reasoning required:    Very high
Tool complexity:       High
Context size:          38k tokens
Current model:         balanced
Selected model:        strong
Confidence:            0.93
Policy:                upgrade
```

---

---

# 3. Non-Goals

JEV Model Router should **not** become the coding agent itself.

It should not own:

- filesystem manipulation
- code execution
- terminal commands
- patch generation
- repository permissions
- MCP server implementation
- interactive coding UX
- agent memory implementation
- task planning performed by the coding agent

Those remain responsibilities of the agent.

JEV only needs enough request metadata to make a routing decision.

---
