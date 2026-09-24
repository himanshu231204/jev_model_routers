# Overview

> Source: `ARCHITECTURE.md` (§1) — verbatim split, do not edit here; propose changes against the source section.

> Back to index: [docs/README.md](./README.md)

---

## 1. Executive Summary

JEV Model Router is an **agent-agnostic model-routing layer for AI coding agents**.

The central design principle is:

```text
Coding Agent != Router != Model Provider
```

The coding agent owns the developer experience, tool execution, permissions, sessions, filesystem access, MCP tools, and agent loop.

JEV Model Router owns the **routing decision**:

```text
            ┌──────────────────────────────┐
            │       Coding Agent           │
            │                              │
            │ Claude / Codex / OpenCode    │
            │ DeepAgents / Hermes / Custom │
            └──────────────┬───────────────┘
                           │
                           │ normalized request
                           ▼
            ┌──────────────────────────────┐
            │      JEV Model Router        │
            │                              │
            │  1. Capture                 │
            │  2. Normalize               │
            │  3. Analyze context         │
            │  4. Ask JEV                 │
            │  5. Apply routing policy    │
            │  6. Resolve concrete model  │
            │  7. Pin model for turn      │
            │  8. Rewrite / forward       │
            └──────────────┬───────────────┘
                           │
                           │ provider-native request
                           ▼
            ┌──────────────────────────────┐
            │      Model / Provider        │
            │                              │
            │ Anthropic / OpenAI / Google │
            │ Groq / OpenRouter / Local   │
            └──────────────────────────────┘
```

The architecture deliberately separates:

- **Agent adapters** — how to integrate with a coding agent.
- **Routing core** — how to decide what capability/model is required.
- **Model registry** — what concrete models are available and what they support.
- **Policy engine** — what decisions are allowed.
- **Transport/proxy layer** — how the request is intercepted and forwarded.
- **State manager** — how model choices are pinned across a turn/tool loop.
- **Observability** — how routing decisions can be inspected without leaking secrets.

The intended result is that adding a new coding agent should require an **adapter**, not a rewrite of the routing engine.

---
