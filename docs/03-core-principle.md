# Core Architectural Principle

> Source: `ARCHITECTURE.md` §4 — verbatim split, do not edit here; propose changes against the source section.

> Back to index: [docs/README.md](./README.md)

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
