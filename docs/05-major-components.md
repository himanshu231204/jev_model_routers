# Major Components

> Source: `ARCHITECTURE.md` §6 — verbatim split, do not edit here; propose changes against the source section.

> Back to index: [docs/README.md](./README.md)

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
