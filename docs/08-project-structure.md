# Project Structure

> Source: `ARCHITECTURE.md` §9 — verbatim split, do not edit here; propose changes against the source section.

> Back to index: [docs/README.md](./README.md)

---

## 9. Project Structure

```
src/jev_router/
├── cli/  · core/  · contracts/  · adapters/  · providers/
├── jev/  · transport/  · state/  · config/  · observability/  · security/
```

Dependency direction: `CLI → Adapters → Core → Contracts`.

Interface contracts: `Router.route()`, `Policy.evaluate()`, `ModelResolver.resolve()`, `AgentAdapter.*`.
