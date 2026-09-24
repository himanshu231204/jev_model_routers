# Examples, Roadmap, and Acceptance

> Source: `ARCHITECTURE.md` (§58, §59, §95, §96, §97, §98, §99, §103, §104) — verbatim split, do not edit here; propose changes against the source section.

> Back to index: [docs/README.md](./README.md)

---

# 58. End-to-End Routing Example

User asks:

```text
"Find why authentication intermittently fails under concurrent requests and fix it."
```

Agent sends request.

Adapter extracts:

```json
{
  "agent": "claude-code",
  "current_model": "claude-sonnet",
  "context_tokens": 32000,
  "tool_count": 14,
  "is_new_turn": true,
  "prompt": "Find why authentication intermittently fails..."
}
```

JEV evaluates:

```text
Task complexity:     high
Reasoning required:  very high
Tool complexity:     high
```

JEV returns:

```json
{
  "choice": "strong",
  "confidence": 0.94
}
```

Policy checks:

```text
explicit override?       no
context too large?       no
strong model available?  yes
confidence sufficient?   yes
```

Resolver:

```text
strong → claude-opus
```

State:

```text
turn-42 = claude-opus
```

Every tool-loop request for turn 42 is rewritten to the same model.

---

---

# 59. Simple Task Example

User:

```text
"Rename this function from getData to getUserData."
```

JEV:

```text
complexity: low
reasoning: low
```

Decision:

```text
fast
```

Resolver:

```text
fast → claude-haiku
```

Result:

```text
lower-cost / lower-latency model
```

---

---

# 95. V1 Implementation Scope

Do not attempt every provider and every agent immediately.

## V1 core

Implement:

```text
✓ normalized request contract
✓ JEV client
✓ policy engine
✓ model registry
✓ resolver
✓ state store
✓ explainability
✓ fail-open fallback
✓ logging
✓ adapter SDK
```

## V1 agents

Recommended initial order:

```text
1. Claude Code
2. Codex
3. OpenCode
```

Then:

```text
4. Hermes
5. DeepAgents
6. custom adapter SDK
```

The reason is architectural diversity: CLI/proxy integrations validate the adapter boundary while the SDK path validates that the core is genuinely agent-independent.

---

---

# 96. V2 Scope

Potential V2:

```text
✓ more agents
✓ provider fallback
✓ cost budgets
✓ routing analytics
✓ policy profiles
✓ plugin marketplace/discovery
✓ distributed state
✓ remote JEV gateway
✓ dashboard
```

---

---

# 97. V3 Scope

Potential future platform capabilities:

```text
✓ learned routing policies
✓ historical task performance feedback
✓ team-level policies
✓ organization budgets
✓ model quality telemetry
✓ benchmark-driven routing
✓ automatic adapter health checks
✓ policy simulation
```

These should only be added after the core adapter architecture is stable.

---

---

# 98. Implementation Phases

## Phase 0 — Contracts

Build:

```text
contracts/
core/decision.py
core/policy.py
```

Deliverable:

```text
NormalizedRequest
JEVDecision
RoutingDecision
ModelSpec
AgentCapabilities
```

---

## Phase 1 — JEV Core

Build:

```text
jev/client.py
jev/schema.py
jev/normalize.py
core/router.py
```

Test with mocked JEV responses.

---

## Phase 2 — Model Registry

Build:

```text
providers/
core/resolver.py
```

Support:

```text
model catalog
capabilities
availability
aliases
```

---

## Phase 3 — State

Build:

```text
state/memory.py
state/store.py
```

Implement:

```text
session
conversation
turn
sub-agent
pinning
```

---

## Phase 4 — Claude Code Adapter

Build:

```text
adapters/claude_code/
```

Validate:

```text
fresh turn detection
model rewriting
tool-loop pinning
sub-agent isolation
streaming
manual override
```

---

## Phase 5 — Codex Adapter

Build:

```text
adapters/codex/
```

Validate:

```text
request detection
provider handling
model rewrite
SSE
session state
```

---

## Phase 6 — OpenCode Adapter

Prefer provider/baseURL integration where supported. OpenCode documents provider configuration and custom base URLs, so the adapter should exploit those extension points rather than depend on fragile UI automation. citeturn817834search2

---

## Phase 7 — Hermes Adapter

Use Hermes' provider/model runtime boundary where possible. Hermes documents both custom provider flows and a runtime provider abstraction. citeturn817834search1turn817834search11

---

## Phase 8 — DeepAgents Adapter

Implement SDK middleware around model invocation.

Validate that:

```text
one logical user turn
    ↓
one JEV decision
    ↓
all agent/tool iterations pinned
```

---

## Phase 9 — Observability

Implement:

```text
metrics
structured events
explain
health checks
adapter diagnostics
```

---

---

# 99. Acceptance Criteria

The project should be considered architecturally complete when all of the following are true.

### Core

```text
[ ] core does not import agent-specific modules
[ ] JEV response is normalized
[ ] policy is independent of vendors
[ ] model registry is independent of agents
[ ] routing is fail-open
```

### Agents

```text
[ ] Claude adapter works
[ ] Codex adapter works
[ ] OpenCode adapter works
[ ] adapter contract tests exist
```

### State

```text
[ ] turn pinning works
[ ] tool loops do not re-route
[ ] sub-agents do not corrupt parent state
```

### Reliability

```text
[ ] JEV timeout has fallback
[ ] malformed JEV response has fallback
[ ] unavailable model has fallback
[ ] unavailable provider has fallback
```

### Security

```text
[ ] secrets never logged
[ ] local proxy binds to localhost
[ ] prompt logging disabled by default
[ ] JEV payload is minimized
```

### Developer experience

```text
[ ] jev-router doctor
[ ] jev-router status
[ ] jev-router explain
[ ] clear debug mode
[ ] documentation for adapter development
```

---

---

# 103. Recommended First Commit Structure

A practical first implementation should start with:

```text
feat: add routing contracts and core architecture
```

Files:

```text
src/jev_router/contracts/requests.py
src/jev_router/contracts/models.py
src/jev_router/contracts/decisions.py
src/jev_router/core/router.py
src/jev_router/core/policy.py
src/jev_router/core/resolver.py
src/jev_router/jev/client.py
src/jev_router/state/memory.py
tests/unit/test_policy.py
tests/unit/test_resolver.py
tests/unit/test_router.py
```

Then add:

```text
feat: add agent adapter interface
```

Then:

```text
feat: add claude code adapter
```

Then:

```text
feat: add codex adapter
```

Then:

```text
feat: add opencode adapter
```

This progression keeps the architecture testable from the start.

---

---

# 104. Architectural Success Criterion

The strongest test of the architecture is this:

> **Can a new coding agent be added without modifying `core/router.py`, `core/policy.py`, or `core/resolver.py`?**

The target answer is:

```text
YES.
```

Adding a new agent should look like:

```text
new-agent/
    adapter.py
    parser.py
    compatibility.py
    tests/
```

and then registering the adapter.

The routing engine should remain unchanged.

That is the central architectural difference between an **agent-specific JEV wrapper** and a true **agent-agnostic JEV model-routing platform**.

---
