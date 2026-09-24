# Success Criterion

> Source: `ARCHITECTURE.md` §14 — verbatim split, do not edit here; propose changes against the source section.

> Back to index: [docs/README.md](./README.md)

---

## 14. Success Criterion

The strongest test: **Can a new coding agent be added without modifying `core/router.py`, `core/policy.py`, or `core/resolver.py`?**

The target answer is: **YES.** Adding a new agent should require only a new `adapters/<name>/` directory + fixtures + tests + registration in the adapter registry.
