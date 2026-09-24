# Routing Invariants (must not regress)

> Source: `ARCHITECTURE.md` §7 — verbatim split, do not edit here; propose changes against the source section.

> Back to index: [docs/README.md](./README.md)

---

## 7. Routing Invariants (must not regress)

- **JEV is the only routing authority.** `TYPESAFE_API_KEY` is read exclusively by `jev/client.py`. `core/classifier.py` must not grow into an independent LLM router.
- **One routing decision per fresh user turn.** Pin selected model for the whole tool loop; tool results, continuations, and telemetry bypass routing.
- **Explicit user model choice always wins** over automatic routing.
- **Fail open, but never silently:** missing key, timeout, 5xx, malformed JEV → fall back to current/default model and record why.
- **State is scoped `agent + session + turn`.** Sub-agent decisions must not overwrite parent session's pinned model. No global `current_model`.
- **Policy sits between JEV and execution:** JEV output → policy (confidence thresholds, override, availability, context protection) → resolver → concrete model.
- **Never log prompts, keys, auth headers, or raw responses** by default.
