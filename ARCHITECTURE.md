# JEV Model Router — Complete Architecture

> **Status:** Target architecture / implementation blueprint
> **Project:** `jev_model_router`
> **Primary goal:** Build an agent-agnostic model router that can sit in front of coding agents (Claude Code, OpenAI Codex, OpenCode, DeepAgents, Hermes Agent, and future/custom agents).
> **Source:** This file is the single source of truth for design. `docs/` holds only an index
> (`docs/README.md`) and the integration quickstart (`docs/00-quickstart.md`) — see §13 below.

---

## 1. Executive Summary

```
Coding Agent != Router != Model Provider
```

The coding agent owns the developer experience, tool execution, permissions, sessions, filesystem access, MCP tools, and agent loop.

JEV Model Router owns the **routing decision**:

```
Coding Agent → normalized request → JEV Model Router → provider-native request → Model/Provider
```

The router's 8 responsibilities:
1. Capture · 2. Normalize · 3. Analyze context · 4. Ask JEV · 5. Apply routing policy · 6. Resolve concrete model · 7. Pin model for turn · 8. Rewrite/forward

The architecture deliberately separates: agent adapters, routing core, model registry, policy engine, transport/proxy layer, state manager, observability.

Adding a new coding agent should require an **adapter**, not a rewrite of the routing engine.

---

## 2. Design Goals

- **Agent agnostic:** Core router works with any adapter. Adding an agent = new adapter + fixtures + tests. No `if agent == "claude":` in core.
- **Per-turn intelligent routing:** One routing decision per fresh user turn, pinned through the entire tool loop.
- **Provider agnostic:** Supports Anthropic, OpenAI, Google, Groq, OpenRouter, Azure OpenAI, Bedrock, Ollama, LM Studio, custom endpoints.
- **Fail open:** Missing key, timeout, 5xx, or malformed JEV response → fall back to current/default model and record why.
- **Explicit human override:** User model choice always wins over automatic routing.
- **Explainability:** Every routing decision is explainable locally (task complexity, confidence, policy, reason).
- **Privacy-safe:** Never log prompts, keys, or auth headers by default. Send minimum data to JEV.
- **Native agent experience:** Preserve tool execution, permissions, sessions, MCP, streaming, agent-specific commands.

---

## 3. Non-Goals

JEV does NOT own: filesystem manipulation, code execution, terminal commands, patch generation, repository permissions, MCP server implementation, interactive coding UX, agent memory, task planning.

---

## 4. Core Architectural Principle

The pipeline contract creates a hard boundary between integration code and routing logic:

```
AgentRequest → NormalizedRequest → JEVDecision → PolicyDecision → ModelResolution → ProviderRequest → AgentResponse
```

Type model:

```
AgentRequest (agent, session, turn, messages, tools, current_model, available_models, metadata)
  → NormalizedRequest (task, context, tools, candidates)
  → JEVDecision (requested_model/tier, confidence, task_complexity, reasoning_required, tool_complexity, context_pressure)
  → PolicyDecision (final_model, reason, changed, fallback, pinned_until)
  → ModelResolution (concrete model from available ∩ agent-compatible ∩ provider-compatible ∩ policy-allowed)
  → Agent-native request
```

---

## 5. High-Level System Architecture

```
Developer → AI Coding Agent → Agent Adapter → Request Normalizer → Routing Context → Feature Extractor
  → Router Core → JEV System → JEV Decision → Policy Engine → Model Resolver
  → Model Registry + Capability Matrix → Final Routing Decision
  → Session/Turn State → Agent Adapter → Transport/Proxy → Provider Adapter → Model Provider API
  → Observability (logs, metrics, explain API)
```

Dependency direction is one-way: **CLI → adapters → core → contracts**. Providers and transports are injected, never imported by policy code.

---

## 6. Major Components

| Component | Responsibility |
|---|---|
| CLI/Launcher | Start router, detect agents, select adapter, load config |
| Agent Adapter Layer | Normalize requests, apply model, detect turns |
| Routing Core | Route: validate → check overrides → ask JEV → policy → resolve → pin |
| Policy Engine | Explicit override, safety constraints, confidence thresholds, cost/latency/cache |
| Model Resolver | Pick concrete model from available ∩ agent-compatible ∩ provider-compatible ∩ policy-allowed |
| State Manager | Turn pinning, sub-agent isolation, session store, lifecycle |
| Transport/Proxy | Forward requests, streaming, local proxy |
| Observability | Structured events, privacy-safe logging, explain API, metrics |
| Security/Privacy | Auth, redaction, local proxy binding, request mutation rules |
| Config/Loader | CLI args > env vars > project config > user config > defaults |

---

## 7. Routing Invariants (must not regress)

- **JEV is the only routing authority.** `TYPESAFE_API_KEY` is read exclusively by `jev/client.py`. `core/classifier.py` must not grow into an independent LLM router.
- **One routing decision per fresh user turn.** Pin selected model for the whole tool loop; tool results, continuations, and telemetry bypass routing.
- **Explicit user model choice always wins** over automatic routing.
- **Fail open, but never silently:** missing key, timeout, 5xx, malformed JEV → fall back to current/default model and record why.
- **State is scoped `agent + session + turn`.** Sub-agent decisions must not overwrite parent session's pinned model. No global `current_model`.
- **Policy sits between JEV and execution:** JEV output → policy (confidence thresholds, override, availability, context protection) → resolver → concrete model.
- **Never log prompts, keys, auth headers, or raw responses** by default.

---

## 8. Architectural Rules

1. **Core never imports an agent adapter** — `core → contracts`, not `core → claude`
2. **Adapter never owns routing policy** — adapters parse and rewrite, they don't decide which model is "better"
3. **JEV never becomes the runtime state manager** — JEV recommends, doesn't own sessions/turns/overrides
4. **One routing decision per fresh turn** — don't re-route every tool call
5. **Explicit user choice wins** — automation optimizes, doesn't override
6. **Fail open** — routing failure must not stop coding
7. **No protocol leakage** — agent-specific formats stay in adapters
8. **Capability first, vendor second** — think "strong reasoning", not "use Claude Opus"
9. **Preserve native behavior** — router should be invisible during normal coding
10. **Minimize sensitive data** — only send what's needed for routing

---

## 9. Project Structure

```
src/jev_router/
├── cli/  · core/  · contracts/  · adapters/  · providers/
├── jev/  · transport/  · state/  · config/  · observability/  · security/
```

Dependency direction: `CLI → Adapters → Core → Contracts`.

Interface contracts: `Router.route()`, `Policy.evaluate()`, `ModelResolver.resolve()`, `AgentAdapter.*`.

---

## 10. Configuration

Precedence: **CLI args > env vars > project config > user config > defaults**.

Default config: `jev.timeout_ms: 1500`, `deadline_ms: 3000`, `max_retries: 1`.

Routing is disabled (passthrough) when `TYPESAFE_API_KEY` is absent.

---

## 11. Testing Rules

- pytest only, `pyproject.toml` sets `testpaths = ["tests"]`.
- Mock the JEV API in all default tests. Live tests are opt-in: `JEV_LIVE_TESTS=1`.
- Adapter tests are fixture-driven (`tests/fixtures/`).
- Every non-trivial change to policy, resolution, overrides, fresh-turn detection, state isolation, or fallback needs a test.

---

## 12. Implementation Phases

Phase 0 — Contracts · Phase 1 — JEV Core · Phase 2 — Model Registry · Phase 3 — State · Phase 4 — Claude Code Adapter · Phase 5 — Codex · Phase 6 — OpenCode · Phase 7 — Hermes · Phase 8 — DeepAgents · Phase 9 — Observability.

All phases are implemented; see `AGENTS.md`'s "Current state of this repo" for what's real vs.
still a gap (e.g. per-turn routing via a live proxy is not yet built).

---

## 13. Documentation Structure

`docs/` holds exactly two files:

```
docs/
├── README.md        # Points to this file and to 00-quickstart.md
└── 00-quickstart.md # Integration guide: install, set TYPESAFE_API_KEY, CLI usage
```

This file (`ARCHITECTURE.md`) is the single source of truth for design — read it directly
rather than a mirrored split. `docs/` previously contained a one-file-per-section split (14
files) plus five empty placeholder directories; both were removed as unnecessary duplication
that had to be kept in sync by hand. `docs/00-quickstart.md` may be hand-edited directly to
stay accurate to `src/`; propose design changes against this file.

---

## 14. Success Criterion

The strongest test: **Can a new coding agent be added without modifying `core/router.py`, `core/policy.py`, or `core/resolver.py`?**

The target answer is: **YES.** Adding a new agent should require only a new `adapters/<name>/` directory + fixtures + tests + registration in the adapter registry.

---

## 15. Reference Material

- OpenCode: provider configuration and custom `baseURL` support — https://opencode.ai/docs/providers
- Hermes Agent: provider/model selection, custom providers, runtime provider resolution — https://github.com/NousResearch/hermes-agent
- `gargpratyush/jev-router`: per-turn routing, model pinning, fail-open, CLI proxying — https://github.com/gargpratyush/jev-router
