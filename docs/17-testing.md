# Testing Architecture

> Source: `ARCHITECTURE.md` (§65, §66, §67) — verbatim split, do not edit here; propose changes against the source section.

> Back to index: [docs/README.md](./README.md)

---

# 65. Testing Architecture

Testing must be heavily contract-driven.

## Unit tests

Test:

- policy
- routing thresholds
- model resolution
- overrides
- context logic
- fallback
- state transitions
- normalization

## Adapter tests

For each adapter:

```text
native request fixture
      ↓
normalize
      ↓
expected NormalizedRequest

routing decision
      ↓
apply_model
      ↓
expected native request
```

## Integration tests

```text
fake agent
  ↓
JEV mock
  ↓
router
  ↓
fake provider
```

No real API key should be necessary.

---

---

# 66. Contract Test Example

A generic adapter contract test should be reusable:

```python
def test_adapter_contract(adapter, fixture):
    normalized = adapter.normalize_request(fixture.request)

    assert normalized.agent == adapter.name
    assert normalized.prompt
    assert normalized.session_id

    rewritten = adapter.apply_model(
        fixture.request,
        fixture.expected_model,
    )

    assert fixture.expected_model in str(rewritten)
```

Every adapter must satisfy the same contract.

---

---

# 67. Golden Fixtures

Store representative request fixtures:

```text
fixtures/
├── claude_code/
│   ├── simple_turn.json
│   ├── tool_loop.json
│   ├── subagent.json
│   └── auxiliary.json
├── codex/
├── opencode/
└── hermes/
```

Update fixtures when upstream agents change request schemas.

---
