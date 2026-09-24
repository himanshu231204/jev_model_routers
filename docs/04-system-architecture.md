# High-Level System Architecture

> Source: `ARCHITECTURE.md` §5 — verbatim split, do not edit here; propose changes against the source section.

> Back to index: [docs/README.md](./README.md)

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
