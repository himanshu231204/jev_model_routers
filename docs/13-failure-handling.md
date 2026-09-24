# Failure Handling and Errors

> Source: `ARCHITECTURE.md` (§30, §31, §32, §77, §78) — verbatim split, do not edit here; propose changes against the source section.

> Back to index: [docs/README.md](./README.md)

---

# 30. Failure Handling

The router must be designed as a fail-open system.

## Failure hierarchy

```text
JEV available
    ↓
normal route

JEV timeout
    ↓
policy fallback

JEV malformed response
    ↓
policy fallback

model unavailable
    ↓
nearest compatible model

provider failure
    ↓
configured provider fallback

router process failure
    ↓
agent's original model path where possible
```

Never transform a routing optimization into a hard availability dependency.

---

---

# 31. Fallback Matrix

```yaml
fallback:
  jev_timeout: keep_current
  jev_unavailable: keep_current
  unknown_model: default
  model_unavailable: next_compatible
  provider_unavailable: alternate_provider
  adapter_error: passthrough
```

---

---

# 32. Model Compatibility Validation

Before applying a routing decision, validate:

```text
model exists?
       ↓
tools supported?
       ↓
streaming supported?
       ↓
context limit sufficient?
       ↓
required output format supported?
       ↓
required reasoning mode supported?
       ↓
provider configured?
```

If a capability is not supported, reject the candidate before request forwarding.

---

---

# 77. Error Taxonomy

Use structured errors:

```text
ConfigurationError
AgentNotFoundError
AdapterError
NormalizationError
JEVTimeoutError
JEVResponseError
PolicyError
ModelResolutionError
ProviderError
TransportError
ProtocolError
```

But most should not crash the coding session.

---

---

# 78. Error Handling Rule

```python
try:
    decision = await router.route(request)
except RoutingError:
    decision = fallback.keep_current(request)
```

The adapter continues normal operation.

Only fatal configuration/launch errors should terminate startup.

---
