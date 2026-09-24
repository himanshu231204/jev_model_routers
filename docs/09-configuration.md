# Configuration

> Source: `ARCHITECTURE.md` §10 — verbatim split, do not edit here; propose changes against the source section.

> Back to index: [docs/README.md](./README.md)

---

## 10. Configuration

Precedence: **CLI args > env vars > project config > user config > defaults**.

Default config: `jev.timeout_ms: 1500`, `deadline_ms: 3000`, `max_retries: 1`.

Routing is disabled (passthrough) when `JEV_API_KEY` is absent.
