# Executive Summary

> Source: `ARCHITECTURE.md` §1 — verbatim split, do not edit here; propose changes against the source section.

> Back to index: [docs/README.md](./README.md)

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
