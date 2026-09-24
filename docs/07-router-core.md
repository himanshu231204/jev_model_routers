# Router Core and JEV Decision

> Source: `ARCHITECTURE.md` (§14, §15, §16, §87, §88, §89) — verbatim split, do not edit here; propose changes against the source section.

> Back to index: [docs/README.md](./README.md)

---

# 14. JEV Router Core

The router core should be completely independent of agent-specific request formats.

```python
class Router:
    async def route(self, context: RoutingContext) -> RoutingDecision:
        """
        1. validate context
        2. check overrides
        3. ask JEV
        4. normalize JEV answer
        5. run policy engine
        6. resolve concrete model
        7. persist/pin decision
        8. return decision
        """
```

The core should not import:

```text
claude
codex
opencode
hermes
```

Those belong to the adapter package.

---

---

# 15. JEV Decision Contract

JEV should be treated as a **decision engine**, not the final authority over runtime state.

Example:

```json
{
  "choice": "claude-sonnet-5",
  "confidence": 0.87,
  "metrics": {
    "task_complexity": 0.72,
    "reasoning_required": 0.81,
    "tool_complexity": 0.64,
    "context_size": 0.31
  }
}
```

Internally normalize it to:

```python
@dataclass
class JEVDecision:
    requested_model: str | None
    requested_tier: str | None

    confidence: float

    task_complexity: float
    reasoning_required: float
    tool_complexity: float
    context_pressure: float

    raw_response: dict | None

    latency_ms: int
```

The rest of the router must not depend on the exact JEV response shape.

This makes a future JEV API version easier to absorb.

---

---

# 16. Capability-Based Routing

Do **not** make the core policy depend permanently on vendor names.

The internal routing language should be capability-oriented.

Recommended capabilities:

```text
fast
balanced
strong
long_context
high_reasoning
coding
tool_use
vision
structured_output
low_latency
low_cost
```

A model then advertises capabilities.

Example:

```yaml
model: claude-sonnet
capabilities:
  reasoning: 8
  coding: 9
  tool_use: 10
  context: 8
  latency: 8
  cost: 6
```

Another model:

```yaml
model: gpt-coding
capabilities:
  reasoning: 9
  coding: 10
  tool_use: 9
  context: 9
  latency: 7
  cost: 7
```

This makes a single JEV decision portable across different agents.

---

---

# 87. Recommended Internal Flow

```python
async def route_request(request):
    normalized = adapter.normalize_request(request)

    if not normalized.is_new_turn:
        return state.get_pinned_model(normalized)

    override = detect_override(normalized)
    if override:
        return resolver.resolve_exact(override)

    context = build_routing_context(normalized)

    jev = await jev_client.route(context)

    policy = policy_engine.evaluate(
        request=normalized,
        jev=jev,
    )

    resolution = resolver.resolve(
        request=normalized,
        decision=policy,
    )

    state.pin(
        normalized,
        resolution,
    )

    events.emit("routing.decision", resolution)

    return resolution
```

This should be the architectural heart of the project.

---

---

# 88. Adapter Flow

```python
async def handle_native_request(raw_request):
    if not adapter.is_new_turn(raw_request):
        model = state.get_pinned_model(adapter.conversation_key(raw_request))
        return forward_with_model(raw_request, model)

    normalized = adapter.normalize_request(raw_request)
    decision = await router.route(normalized)

    rewritten = adapter.apply_model(
        raw_request,
        decision.model,
    )

    return transport.forward(rewritten)
```

The adapter should contain no routing intelligence.

---

---

# 89. What Belongs in Core vs Adapter

| Concern | Core | Adapter |
|---|---|---|
| JEV request | ✓ |  |
| Confidence policy | ✓ |  |
| Cost policy | ✓ |  |
| Model resolution | ✓ |  |
| Turn pinning | ✓ |  |
| Session state | ✓ |  |
| Request normalization |  | ✓ |
| Agent request parsing |  | ✓ |
| Agent model rewriting |  | ✓ |
| Agent-specific protocol |  | ✓ |
| Native UI/status |  | ✓ |
| Provider-specific API quirks |  | provider layer |

---
