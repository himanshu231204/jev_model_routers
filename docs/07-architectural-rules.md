# Architectural Rules

> Source: `ARCHITECTURE.md` §8 — verbatim split, do not edit here; propose changes against the source section.

> Back to index: [docs/README.md](./README.md)

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
