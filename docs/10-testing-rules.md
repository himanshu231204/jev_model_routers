# Testing Rules

> Source: `ARCHITECTURE.md` §11 — verbatim split, do not edit here; propose changes against the source section.

> Back to index: [docs/README.md](./README.md)

---

## 11. Testing Rules

- pytest only, `pyproject.toml` sets `testpaths = ["tests"]`.
- Mock the JEV API in all default tests. Live tests are opt-in: `JEV_LIVE_TESTS=1`.
- Adapter tests are fixture-driven (`tests/fixtures/`).
- Every non-trivial change to policy, resolution, overrides, fresh-turn detection, state isolation, or fallback needs a test.
