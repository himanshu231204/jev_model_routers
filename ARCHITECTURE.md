# JEV Model Router — Complete Architecture

> **Status:** Target architecture / implementation blueprint
> **Project:** `jev_model_router`
> **Primary goal:** Build an agent-agnostic model router that can sit in front of coding agents (Claude Code, OpenAI Codex, OpenCode, DeepAgents, Hermes Agent, and future/custom agents).
> **Source:** This file is the single source of truth. Detailed sections are split into `docs/` (19 indexed files). See §93 below.

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
| Agent Adapter Layer | Normalize requests, apply model, detect turns (107-§106) |
| Routing Core | Route: validate → check overrides → ask JEV → policy → resolve → pin (§14) |
| Policy Engine | Explicit override, safety constraints, confidence thresholds, cost/latency/cache (§20-§22, §46-§49) |
| Model Resolver | Pick concrete model from available ∩ agent-compatible ∩ provider-compatible ∩ policy-allowed (§17-§19) |
| State Manager | Turn pinning, sub-agent isolation, session store, lifecycle (§23-§25, §41-§45) |
| Transport/Proxy | Forward requests, streaming, local proxy (§26-§27, §71-§72) |
| Observability | Structured events, privacy-safe logging, explain API, metrics (§50-§52, §74-§76) |
| Security/Privacy | Auth, redaction, local proxy binding, request mutation rules (§28-§32, §68-§70) |
| Config/Loader | CLI args > env vars > project config > user config > defaults (§53-§54) |

---

## 7. Routing Invariants (must not regress)

- **JEV is the only routing authority.** `JEV_API_KEY` is read exclusively by `jev/client.py`. `core/classifier.py` must not grow into an independent LLM router.
- **One routing decision per fresh user turn.** Pin selected model for the whole tool loop; tool results, continuations, and telemetry bypass routing.
- **Explicit user model choice always wins** over automatic routing.
- **Fail open, but never silently:** missing key, timeout, 5xx, malformed JEV → fall back to current/default model and record why.
- **State is scoped `agent + session + turn`.** Sub-agent decisions must not overwrite parent session's pinned model. No global `current_model`.
- **Policy sits between JEV and execution:** JEV output → policy (confidence thresholds, override, availability, context protection) → resolver → concrete model.
- **Never log prompts, keys, auth headers, or raw responses** by default.

---

## 8. Architectural Rules (§100)

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

Full layout with all files: **§55** in `docs/16-project-structure.md`.

Dependency direction (§56): `CLI → Adapters → Core → Contracts`.

Interface contracts (§57): `Router.route()`, `Policy.evaluate()`, `ModelResolver.resolve()`, `AgentAdapter.*`.

---

## 10. Configuration

Precedence: **CLI args > env vars > project config > user config > defaults**.

Default config: `jev.timeout_ms: 1500`, `deadline_ms: 3000`, `max_retries: 1`.

Routing is disabled (passthrough) when `JEV_API_KEY` is absent.

Full config schema and examples: **§53-§54** in `docs/15-configuration-cli.md`.

---

## 11. Testing Rules

- pytest only, `pyproject.toml` sets `testpaths = ["tests"]`.
- Mock the JEV API in all default tests. Live tests are opt-in: `JEV_LIVE_TESTS=1`.
- Adapter tests are fixture-driven (`tests/fixtures/`).
- Every non-trivial change to policy, resolution, overrides, fresh-turn detection, state isolation, or fallback needs a test.

Full testing architecture: **§65-§67** in `docs/17-testing.md`.

---

## 12. Implementation Phases

Phase 0 — Contracts · Phase 1 — JEV Core · Phase 2 — Model Registry · Phase 3 — State · Phase 4 — Claude Code Adapter · Phase 5 — Codex · Phase 6 — OpenCode · Phase 7 — Hermes · Phase 8 — DeepAgents · Phase 9 — Observability.

Full roadmap and acceptance criteria: **§95-§99** in `docs/18-roadmap.md`.

---

## 13. Documentation Structure (§93)

The `docs/` directory contains a verbatim split of this architecture document into 19 indexed files:

```
docs/
├── 00-quickstart.md         # Integration guide, all three strategies
├── README.md                    # Index and section-to-file map (106 sections)
├── 01-overview.md               # §1   Executive Summary
├── 02-design-goals.md           # §2-§3  Design goals, non-goals
├── 03-core-principles.md        # §4, §100, §106  Core principles and rules
├── 04-system-architecture.md    # §5, §101, §102  System diagram and core abstraction
├── 05-agent-adapters.md         # §7-§9, §33-§40  Adapter layer, types, plugins
├── 06-request-models.md         # §10-§13  Normalized request, repo context, tools, routing context
├── 07-router-core.md            # §14-§16, §87-§89  Router core, JEV decision, internal flows
├── 08-models-registry.md        # §17-§19, §83-§86  Registry, resolution, capability matrix
├── 09-policy-engine.md          # §20-§22, §46-§49, §60  Policy, overrides, confidence, caching
├── 10-turn-state.md             # §23-§25, §41-§45, §81-§82  Turn pinning, sub-agents, concurrency
├── 11-transport-proxy.md        # §26-§27, §71-§72, §80  Transport, proxy, streaming, WebSocket
├── 12-security-privacy.md       # §28-§29, §68-§70  Auth, privacy, proxy security, mutation rules
├── 13-failure-handling.md       # §30-§32, §77-§78  Failure hierarchy, fallback, error taxonomy
├── 14-observability.md          # §50-§52, §74-§76  Observability, logging, explain, metrics
├── 15-configuration-cli.md      # §6, §53-§54, §61-§64, §73, §79  CLI, config, doctor, compat
├── 16-project-structure.md      # §55-§57, §90-§94  Project layout, dependencies, contracts, README
├── 17-testing.md                # §65-§67  Testing architecture, contract tests, fixtures
├── 18-roadmap.md                # §58-§59, §95-§99  Routing examples, V1-V3, phases, acceptance
└── 19-references.md             # §105  Reference material
```

> **Note:** This file (`ARCHITECTURE.md`) remains the single source of truth. `docs/*` are verbatim splits — do not edit them; propose changes against the source section here.

---

## 14. Success Criterion (§104)

The strongest test: **Can a new coding agent be added without modifying `core/router.py`, `core/policy.py`, or `core/resolver.py`?**

The target answer is: **YES.** Adding a new agent should require only a new `adapters/<name>/` directory + fixtures + tests + registration in the adapter registry.

---

## 15. Reference Material (§105)

- OpenCode: provider configuration and custom `baseURL` support — https://opencode.ai/docs/providers
- Hermes Agent: provider/model selection, custom providers, runtime provider resolution — https://github.com/NousResearch/hermes-agent
- `gargpratyush/jev-router`: per-turn routing, model pinning, fail-open, CLI proxying — https://github.com/gargpratyush/jev-router
