# Model Registry and Resolution

> Source: `ARCHITECTURE.md` (§17, §18, §19, §83, §84, §85, §86) — verbatim split, do not edit here; propose changes against the source section.

> Back to index: [docs/README.md](./README.md)

---

# 17. Model Registry

The model registry is the source of truth for concrete models.

```python
@dataclass
class ModelSpec:
    id: str
    provider: str
    family: str

    capabilities: ModelCapabilities
    limits: ModelLimits
    pricing: PricingInfo | None

    api_mode: str
    input_formats: list[str]
    tool_support: bool
    streaming: bool

    aliases: list[str]
    enabled: bool
```

Example YAML:

```yaml
models:
  - id: anthropic/claude-sonnet
    provider: anthropic
    family: claude
    tier: balanced
    capabilities:
      coding: 9
      reasoning: 8
      tool_use: 10
      context: 9
      speed: 8
    features:
      tools: true
      streaming: true

  - id: openai/coding-strong
    provider: openai
    family: gpt
    tier: strong
    capabilities:
      coding: 10
      reasoning: 9
      tool_use: 10
      context: 9
      speed: 7
```

---

---

# 18. Model Resolution

JEV should ideally choose the **required capability/tier**.

The Model Resolver chooses the actual model.

```text
JEV
 ↓
strong
 ↓
Model Resolver
 ├── Claude available?
 ├── OpenAI available?
 ├── provider constraints?
 ├── context limit?
 ├── tool support?
 ├── user allowlist?
 └── cost policy?
 ↓
concrete model
```

Resolver contract:

```python
class ModelResolver:
    def resolve(
        self,
        requested_capability: str,
        candidates: list[ModelSpec],
        context: RoutingContext,
    ) -> ModelResolution:
        ...
```

---

---

# 19. Model Resolution Example

Suppose JEV returns:

```text
strong, confidence=0.92
```

For Claude Code:

```text
strong → Claude Opus family
```

For Codex:

```text
strong → configured OpenAI reasoning/coding model
```

For OpenCode:

```text
strong → configured strong provider model
```

For Hermes:

```text
strong → provider:model configured in Hermes-compatible format
```

For a custom agent:

```text
strong → best candidate satisfying capability score
```

JEV does not need to know the agent-specific model identifier.

---

---

# 83. Model Availability Discovery

Model catalogs should be obtained in this order:

```text
1. Agent's native catalog
2. Provider API catalog
3. Configured static model registry
4. Static fallback
```

The router should never assume an exact model ID exists simply because a model family exists.

---

---

# 84. Exact Model vs Tier

Support both.

### Tier routing

```text
fast
balanced
strong
long
```

### Exact routing

```text
anthropic/...
openai/...
provider/model
```

Use exact model only when:

- the user explicitly selected it, or
- JEV selected an exact model with sufficient confidence, or
- policy configuration explicitly permits it.

---

---

# 85. Model Capability Matrix

Example:

| Capability | Fast | Balanced | Strong | Long |
|---|---:|---:|---:|---:|
| Coding | 7 | 9 | 10 | 10 |
| Reasoning | 5 | 8 | 10 | 10 |
| Tool use | 7 | 9 | 10 | 10 |
| Context | 6 | 8 | 9 | 10 |
| Speed | 10 | 8 | 6 | 4 |
| Cost efficiency | 10 | 8 | 5 | 3 |

These are configuration concepts, not universal claims about current models.

---

---

# 86. Routing Formula

The router itself should not replace JEV with a complicated hand-built formula.

However, the policy engine can calculate a compatibility score:

```text
candidate_score =
    capability_fit
  + context_fit
  + tool_fit
  + availability
  + policy_fit
  - cost_penalty
  - latency_penalty
```

JEV answers:

```text
What level/capability does this task require?
```

The resolver answers:

```text
Which available model best satisfies that requirement?
```

This separation is fundamental.

---
