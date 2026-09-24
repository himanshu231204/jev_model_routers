# Policy Engine

> Source: `ARCHITECTURE.md` (§20, §21, §22, §46, §47, §48, §49, §60) — verbatim split, do not edit here; propose changes against the source section.

> Back to index: [docs/README.md](./README.md)

---

# 20. Routing Policy Engine

The policy engine sits between JEV and execution.

This is critical because JEV can recommend a model while runtime constraints may prohibit it.

```text
JEV Decision
      ↓
Policy Engine
      ├── explicit user override?
      ├── model available?
      ├── confidence sufficient?
      ├── context too large?
      ├── model supports required tools?
      ├── cost limit exceeded?
      ├── provider unavailable?
      └── session already pinned?
      ↓
Allowed / modified decision
```

Recommended precedence:

```text
1. Explicit user model selection
2. Hard safety/runtime constraints
3. Session/turn pinning rules
4. JEV recommendation
5. Cost/latency optimization
6. Default fallback
```

---

---

# 21. Explicit Overrides

Examples:

```text
use opus
use sonnet
use strong model
use fast model
use gpt-x
use claude-sonnet
```

These should override automatic routing where the syntax is unambiguous.

Implementation:

```python
@dataclass
class UserOverride:
    kind: Literal["exact_model", "tier", "disable_router"]
    value: str
```

The adapter can also support native model selection outside the prompt.

---

---

# 22. Confidence Policy

Recommended behavior:

```text
confidence < low_threshold
    ↓
Do not perform aggressive downgrade/upgrade
```

Example policy:

```yaml
routing:
  confidence:
    low: 0.30
    medium: 0.60
    high: 0.85
```

Suggested interpretation:

```text
< 0.30
    preserve current model

0.30 - 0.60
    conservative transition

0.60 - 0.85
    normal routing

> 0.85
    normal routing + exact model allowed
```

Thresholds should be configurable rather than hard-coded.

---

---

# 46. Routing Policies

Support multiple policies rather than one hard-coded policy.

```text
policies/
├── default
├── cost-first
├── latency-first
├── quality-first
└── conservative
```

Example:

### Default

Balance cost and quality.

### Cost-first

Prefer lower-cost models when confidence permits.

### Quality-first

Prefer stronger models for ambiguous or high-risk coding tasks.

### Latency-first

Prefer fast models for interactive workflows.

### Conservative

Avoid downgrades and remain close to the current model.

---

---

# 47. Cost Policy

The model registry can optionally define token pricing metadata.

```yaml
pricing:
  input_per_million: 2.00
  output_per_million: 8.00
```

The policy engine can then enforce:

```text
maximum cost per turn
maximum cost per session
maximum premium upgrades per hour
```

These must be opt-in and configurable.

---

---

# 48. Latency Policy

JEV itself adds routing latency.

The router should track:

```text
JEV latency
model selection latency
proxy overhead
upstream TTFT
full completion latency
```

A routing decision should have a configurable latency budget.

Example:

```yaml
routing:
  max_jev_latency_ms: 1500
  hard_deadline_ms: 3000
```

If exceeded:

```text
keep current model
```

---

---

# 49. Caching JEV Decisions

Do not blindly cache by prompt string because coding context matters.

Potential cache key:

```text
hash(
  normalized prompt,
  task type,
  available model capabilities,
  policy version
)
```

Use very short TTL by default.

Avoid caching sensitive raw prompts to disk.

---

---

# 60. Model Switch Guard

Model switching should be controlled carefully.

Before changing:

```python
should_switch(
    current_model,
    target_model,
    context_tokens,
    confidence,
    policy,
)
```

Possible result:

```json
{
  "switch": false,
  "reason": "downgrade_not_worth_context_rebuild"
}
```

This prevents routing from making the workflow slower merely to save a small amount of model cost.

---
