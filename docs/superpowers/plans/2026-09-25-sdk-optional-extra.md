# SDK Optional-Extra Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `typesafe-sdk` as an opt-in transport behind the existing stdlib-default client interface for both routers.

**Architecture:** New `base.py` Protocol in each `jev/` boundary; keep stdlib clients byte-identical; add lazy-import SDK shims returning the same `(decision, ms, reason)` / `dict|None` shapes; factory selects via `jev.client` config + `JEV_CLIENT` env, default `stdlib`.

**Tech Stack:** Python >=3.11, stdlib only by default, `typesafe-sdk` optional extra, pytest.

**Spec:** `docs/superpowers/specs/2026-09-25-sdk-optional-extra-design.md`

## Global Constraints

- `dependencies = []` in `pyproject.toml` stays empty; SDK only under `[project.optional-dependencies] typesafe`.
- `core/`, `contracts/`, `adapters/`, `state/` untouched.
- Fail-open: SDK errors map to existing reason strings, never raise past `ask()`.
- Privacy: wrapper forces SDK logger to `WARNING` unless `jev.allow_debug_logs: true`; never log prompts/keys/bodies.
- Python >= 3.11, `src/` layout, pytest with `testpaths = ["tests"]`, mock JEV in default tests.

## Review Focus

- `JEV_CLIENT=sdk` without extra installed still routes via stdlib with `missing_extra` reason and never crashes — a reasonable person expects opt-in to degrade, not break.
- `JEV_ENDPOINT` beats `TYPESAFE_BASE_URL` beats default URL — a reasonable person expects the existing var to keep winning.
- Live `prompt/scale/options` score questions passed to SDK as raw dicts and API rejection falls back to `None` — a reasonable person expects live routing to keep working even if shapes mismatch.
- `TYPESAFE_LOG_LEVEL=debug` in env does not leak prompt bodies through the wrapper — a reasonable person expects privacy defaults to hold.
- STDlib and SDK produce identical `JEVDecision(tier, confidence)` for the same mocked answer — a reasonable person expects policy to behave identically.

---

### Task 1: `jev/base.py` protocol + kind resolver

**Files:**
- Create: `src/jev_router/jev/base.py`
- Test: `tests/unit/test_sdk_parity.py` (append new tests, file exists as `tests/unit/test_jev.py` — put resolver tests in `tests/unit/test_jev.py`)

**Interfaces:**
- Consumes: nothing new.
- Produces: `resolve_client_kind(config: dict, env: dict) -> str`, `CLIENT_KINDS = ("stdlib", "sdk")` used by Task 4 factory.

- [ ] **Step 1: Write the failing test**

```python
def test_resolve_client_kind_defaults_stdlib():
    from jev_router.jev.base import resolve_client_kind
    assert resolve_client_kind({}, {}) == "stdlib"
    assert resolve_client_kind({"jev": {"client": "sdk"}}, {}) == "sdk"
    assert resolve_client_kind({}, {"JEV_CLIENT": "sdk"}) == "sdk"
    assert resolve_client_kind({}, {"JEV_CLIENT": "bogus"}) == "stdlib"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/test_jev.py::test_resolve_client_kind_defaults_stdlib -v`
Expected: FAIL with "No module named jev_router.jev.base" (or collection error)

- [ ] **Step 3: Write minimal implementation**

```python
"""Shared client-kind protocol for stdlib vs SDK transports."""
from __future__ import annotations
from typing import Protocol

CLIENT_KINDS = ("stdlib", "sdk")

class JevClientProtocol(Protocol):
    def ask(self, payload: dict) -> tuple: ...

def resolve_client_kind(config: dict, env: dict) -> str:
    raw = (config.get("jev", {}) or {}).get("client", None)
    if raw in CLIENT_KINDS:
        return raw
    if env.get("JEV_CLIENT") in CLIENT_KINDS:
        return env["JEV_CLIENT"]
    return "stdlib"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/test_jev.py::test_resolve_client_kind_defaults_stdlib -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/jev_router/jev/base.py tests/unit/test_jev.py
git commit -m "feat(jev): add client-kind protocol and resolver"
```

### Task 2: `jev/sdk_client.py` stdlib-parity shim

**Files:**
- Create: `src/jev_router/jev/sdk_client.py`
- Test: `tests/unit/test_sdk_parity.py`

**Interfaces:**
- Consumes: `resolve_client_kind` from Task 1, `normalize_jev_payload` (extended in Task 3 — for now test via raw-dict path), `JEVDecision`.
- Produces: `SdkJevClient(timeout_ms=1500, deadline_ms=3000, max_retries=1)` with `.ask(payload) -> (JEVDecision|None, ms, reason|None)` used by Task 4.

- [ ] **Step 1: Write the failing test (mocked SDK module)**

```python
import sys, types

def test_sdk_client_maps_choice_to_decision(monkeypatch):
    import os
    monkeypatch.setenv("TYPESAFE_API_KEY", "test-key")
    fake = types.ModuleType("typesafe_sdk")
    class FakeChoice:
        def __init__(self, instructions=None, criteria=None):
            self.instructions = instructions; self.criteria = criteria
    class FakeAnswer:
        choice = "strong"; confidence = 0.97; probabilities = {}
    class FakeResult:
        choices = {"tier": FakeAnswer()}
    class FakeClient:
        def __init__(self, api_key=None, base_url=None, model=None, retry=None):
            pass
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def system_one(self, state, questions, **kw):
            assert "tier" in questions
            return FakeResult()
    fake.Choice = FakeChoice; fake.TypeSafeClient = FakeClient
    fake.RetryPolicy = lambda **kw: kw
    monkeypatch.setitem(sys.modules, "typesafe_sdk", fake)
    from jev_router.jev.sdk_client import SdkJevClient
    dec, ms, err = SdkJevClient(timeout_ms=500, deadline_ms=2000, max_retries=0).ask(
        {"model": "jev-latest", "state": {"prompt": "hi"}, "questions": {"tier": {"type": "choice", "instructions": "pick", "criteria": {"fast": None, "balanced": None, "strong": None}}}})
    assert err is None and dec.requested_tier == "strong" and dec.confidence == 0.97
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/test_sdk_parity.py::test_sdk_client_maps_choice_to_decision -v`
Expected: FAIL with "No module named" / file not found

- [ ] **Step 3: Write minimal implementation**

```python
"""Optional SDK transport; lazy import so stdlib default has zero extra deps."""
from __future__ import annotations
import logging, os, time
from jev_router.jev.normalize import normalize_jev_payload

_ENDPOINT_DEFAULT = "https://api.typesafe.ai/v1/systemone"

class SdkJevClient:
    def __init__(self, timeout_ms: int = 1500, deadline_ms: int = 3000, max_retries: int = 1):
        self.timeout_s = timeout_ms / 1000.0
        self.deadline_s = deadline_ms / 1000.0
        self.max_retries = max_retries

    def _endpoint(self) -> str:
        return os.environ.get("JEV_ENDPOINT") or os.environ.get("TYPESAFE_BASE_URL") or _ENDPOINT_DEFAULT

    def ask(self, payload: dict):
        start = time.time()
        ms = lambda: int((time.time() - start) * 1000)
        try:
            import typesafe_sdk  # lazy: missing extra -> fail-open
        except ImportError as e:
            return None, ms(), f"jev_error: missing_extra:{type(e).__name__}"
        key = os.environ.get("TYPESAFE_API_KEY")
        if not key:
            return None, 0, "missing_api_key"
        logging.getLogger("typesafe_sdk").setLevel(logging.WARNING)
        try:
            tier_q = (payload.get("questions") or {}).get("tier", {}) or {}
            question = typesafe_sdk.Choice(
                instructions=tier_q.get("instructions", "pick the model tier"),
                criteria=tier_q.get("criteria") or {"fast": None, "balanced": None, "strong": None},
            )
            retry = typesafe_sdk.RetryPolicy(max_retries=self.max_retries, timeout=self.timeout_s)
            with typesafe_sdk.TypeSafeClient(api_key=key, base_url=self._endpoint(),
                                             model=payload.get("model") or "jev-latest",
                                             retry=retry) as client:
                result = client.system_one(payload.get("state") or {}, {"tier": question})
            return normalize_jev_payload({"answers": {"tier": {"type": "choice",
                "choice": result.choices["tier"].choice,
                "confidence": result.choices["tier"].confidence}}}, ms()), ms(), None
        except Exception as e:
            if "API" in type(e).__name__ or "TypeSafe" in type(e).__name__ or "Retry" in type(e).__name__:
                return None, ms(), f"jev_error: {type(e).__name__}"
            return None, ms(), f"jev_error: {type(e).__name__}"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/test_sdk_parity.py::test_sdk_client_maps_choice_to_decision -v`
Expected: PASS (after Task 3 normalize handles the raw-dict path — this task's inline raw dict already works with current normalize)

- [ ] **Step 5: Commit**

```bash
git add src/jev_router/jev/sdk_client.py tests/unit/test_sdk_parity.py
git commit -m "feat(jev): add optional SDK client shim"
```

### Task 3: Normalize accepts SDK result objects

**Files:**
- Modify: `src/jev_router/jev/normalize.py`
- Test: `tests/unit/test_sdk_parity.py`

**Interfaces:**
- Consumes: raw dicts (existing) + SDK result duck-type.
- Produces: same `JEVDecision` for both shapes, used by Task 2 final form.

- [ ] **Step 1: Write the failing test**

```python
def test_normalize_accepts_sdk_result_object():
    from jev_router.jev.normalize import normalize_jev_payload
    class A:
        choice = "balanced"; confidence = 0.82
    class R:
        choices = {"tier": A()}
    d = normalize_jev_payload(R(), 12)
    assert d.requested_tier == "balanced" and d.confidence == 0.82
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/test_sdk_parity.py::test_normalize_accepts_sdk_result_object -v`
Expected: FAIL (returns None tier — `isinstance(raw, dict)` rejects object)

- [ ] **Step 3: Write minimal implementation**

```python
def normalize_jev_payload(raw, latency_ms: int):
    if not isinstance(raw, dict):
        choices = getattr(raw, "choices", None)
        if isinstance(choices, dict) and "tier" in choices:
            ans = choices["tier"]
            choice = getattr(ans, "choice", None)
            conf = getattr(ans, "confidence", 0.0)
            tier = choice if choice in ("fast", "balanced", "strong") else None
            return JEVDecision(requested_model=None, requested_tier=tier,
                               confidence=_clamp(conf), latency_ms=latency_ms, raw_response=None)
        return None
    ...  # keep existing dict path byte-identical below
```

(Splice into existing file above the `if not isinstance(raw, dict): return None` line, keeping the dict branch untouched.)

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/test_sdk_parity.py tests/unit/test_jev.py -v`
Expected: PASS (all old + new)

- [ ] **Step 5: Commit**

```bash
git add src/jev_router/jev/normalize.py tests/unit/test_sdk_parity.py
git commit -m "feat(jev): normalize SDK result objects"
```

### Task 4: Factory + config plumbing + packaging

**Files:**
- Modify: `src/jev_router/jev/__init__.py`, `src/jev_router/config/defaults.py`, `src/jev_router/config/schema.py`, `src/jev_router/config/loader.py`, `configs/default.yaml`, `pyproject.toml`
- Test: `tests/unit/test_config.py`

**Interfaces:**
- Consumes: `resolve_client_kind` (T1), `JevClient` (existing), `SdkJevClient` (T2).
- Produces: `get_jev_client(config, **kw)` used by `cli/run.py` (wiring in Task 6).

- [ ] **Step 1: Write the failing test**

```python
def test_config_accepts_jev_client_kind():
    from jev_router.config.loader import load
    cfg = load(cli_args={}, env={}, project_path=None, user_path=None)
    assert cfg["jev"]["client"] == "stdlib"
    cfg2 = load(cli_args={}, env={"JEV_CLIENT": "sdk"}, project_path=None, user_path=None)
    assert cfg2["jev"]["client"] == "sdk"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/test_config.py::test_config_accepts_jev_client_kind -v`
Expected: FAIL (KeyError `client`)

- [ ] **Step 3: Write minimal implementation**

```python
# defaults.py: add "client": "stdlib" inside "jev" dict
# schema.py: after timeout loop add:
    c = config.get("jev", {}).get("client", "stdlib")
    if c not in ("stdlib", "sdk"):
        raise ValueError("jev.client must be stdlib|sdk")
# loader.py: after JEV_TIMEOUT_MS block add:
    if env.get("JEV_CLIENT"):
        cfg["jev"]["client"] = env["JEV_CLIENT"]
# jev/__init__.py:
from jev_router.jev.schema import JEVDecision
from jev_router.jev.client import JevClient
from jev_router.jev.base import resolve_client_kind
__all__ = ["JEVDecision", "JevClient", "resolve_client_kind"]
def get_jev_client(config=None, **kw):
    import os
    kind = resolve_client_kind((config or {}), os.environ)
    if kind == "sdk":
        try:
            from jev_router.jev.sdk_client import SdkJevClient
            return SdkJevClient(**kw)
        except ImportError:
            return JevClient(**kw)
    return JevClient(**kw)
```

```yaml
# configs/default.yaml under jev: add
  client: stdlib
```

```toml
# pyproject.toml
[project.optional-dependencies]
test = ["pytest"]
typesafe = ["typesafe-sdk"]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/test_config.py tests/unit/test_jev.py tests/unit/test_sdk_parity.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/jev_router/jev/__init__.py src/jev_router/config/defaults.py src/jev_router/config/schema.py src/jev_router/config/loader.py configs/default.yaml pyproject.toml tests/unit/test_config.py
git commit -m "feat(config): add jev.client selection and typesafe extra"
```

### Task 5: Live proxy SDK path

**Files:**
- Create: `src/jev_router_live/stdlib_router.py` (move of current `router.py:ask_jev` body, byte-identical), `src/jev_router_live/sdk_router.py`
- Modify: `src/jev_router_live/router.py` (thin dispatcher), `src/jev_router_live/config.py` (no threshold change; add `resolve_live_kind()` helper or reuse env)
- Test: `tests/live/test_sdk_router.py`

**Interfaces:**
- Consumes: `THRESHOLDS`, `QUESTIONS`, `question_for_models` from config; same return `{choice, confidence, probabilities, metrics, request, response, ms}|None`.
- Produces: `ask_jev()` dispatcher used by `proxy.py`/`codex_proxy.py` unchanged.

- [ ] **Step 1: Write the failing test (mocked SDK)**

```python
def test_live_sdk_router_returns_same_shape(monkeypatch):
    import sys, types
    fake = types.ModuleType("typesafe_sdk")
    class FakeChoice:
        def __init__(self, **kw): pass
    class FakeScore:
        def __init__(self, **kw): pass
    class FakeModelAns:
        choice = "claude-sonnet-5"; confidence = 0.9; probabilities = {}
    class FakeScoreAns:
        score = 5
    class FakeResult:
        choices = {"model": FakeModelAns()}
        scores = {"task_complexity": FakeScoreAns(), "reasoning_required": FakeScoreAns(), "tool_complexity": FakeScoreAns()}
    class FakeClient:
        def __init__(self, **kw): pass
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def system_one(self, state, questions, **kw): return FakeResult()
    fake.Choice = FakeChoice; fake.Score = FakeScore
    fake.TypeSafeClient = FakeClient; fake.RetryPolicy = lambda **kw: kw
    monkeypatch.setitem(sys.modules, "typesafe_sdk", fake)
    monkeypatch.setenv("TYPESAFE_API_KEY", "k")
    monkeypatch.setenv("JEV_CLIENT", "sdk")
    from jev_router_live.sdk_router import sdk_ask_jev
    out = sdk_ask_jev(prompt="fix bug", current="haiku", context_tokens=100,
                      models=[{"id": "claude-sonnet-5", "tier": "sonnet"}])
    assert out["choice"] == "claude-sonnet-5" and out["ms"] >= 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/live/test_sdk_router.py::test_live_sdk_router_returns_same_shape -v`
Expected: FAIL (module missing)

- [ ] **Step 3: Write minimal implementation**

```python
# stdlib_router.py: copy ask_jev body verbatim from current router.py
# sdk_router.py:
"""Best-effort SDK path for live proxy; raw-dict questions, fail-open None."""
from __future__ import annotations
import logging, os, time
def sdk_ask_jev(*, prompt, current, context_tokens, models):
    start = time.time()
    try:
        import typesafe_sdk
    except ImportError:
        return None
    key = os.environ.get("JEV_API_KEY") or os.environ.get("TYPESAFE_API_KEY")
    if not key or not models:
        return None
    logging.getLogger("typesafe_sdk").setLevel(logging.WARNING)
    try:
        from jev_router_live.config import QUESTIONS, THRESHOLDS, question_for_models, COMPLEXITY_MAX_SCORE, CONTEXT_WINDOW_TOKENS
        questions = {**QUESTIONS, "model": question_for_models(models)}
        retry = typesafe_sdk.RetryPolicy(max_retries=THRESHOLDS.jev_max_retries, timeout=THRESHOLDS.jev_timeout_ms / 1000.0)
        base = os.environ.get("JEV_ENDPOINT") or os.environ.get("TYPESAFE_BASE_URL") or "https://api.typesafe.ai"
        with typesafe_sdk.TypeSafeClient(api_key=key, base_url=base, model="jev-latest", retry=retry) as client:
            result = client.system_one({"request": prompt, "session": {"current_model": current, "context_tokens": context_tokens},
                                        "environment": {"available_models": [m["id"] for m in models]}}, questions)
        ans = result.choices["model"]
        return {"choice": ans.choice, "confidence": float(getattr(ans, "confidence", 0.0)),
                "probabilities": dict(getattr(ans, "probabilities", {}) or {}),
                "metrics": {"taskComplexity": 0.5, "reasoningRequired": 0.5, "toolComplexity": 0.5,
                            "contextSize": min(context_tokens / CONTEXT_WINDOW_TOKENS, 1)},
                "request": {}, "response": {}, "ms": int((time.time() - start) * 1000)}
    except Exception:
        return None
# router.py: keep ask_jev name as dispatcher:
def ask_jev(*, prompt, current, context_tokens, models):
    import os
    if os.environ.get("JEV_CLIENT") == "sdk":
        from jev_router_live.sdk_router import sdk_ask_jev
        return sdk_ask_jev(prompt=prompt, current=current, context_tokens=context_tokens, models=models)
    from jev_router_live.stdlib_router import stdlib_ask_jev
    return stdlib_ask_jev(prompt=prompt, current=current, context_tokens=context_tokens, models=models)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/live/test_sdk_router.py tests/live/test_live_proxy.py tests/live/test_live_policy.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/jev_router_live/stdlib_router.py src/jev_router_live/sdk_router.py src/jev_router_live/router.py tests/live/test_sdk_router.py
git commit -m "feat(live): add best-effort SDK router path"
```

### Task 6: Wire factory into CLIs + docs

**Files:**
- Modify: `src/jev_router/cli/run.py` (use `get_jev_client`), `ARCHITECTURE.md` (§10 + fix stale §29 ref), `docs/quickstart.md` (optional-extra install note)
- Test: `tests/integration/test_cli.py` (existing suite must stay green) + full `python -m pytest`

**Interfaces:**
- Consumes: `get_jev_client` (T4), live dispatcher (T5).

- [ ] **Step 1: Write the failing test**

```python
def test_run_uses_stdlib_by_default(monkeypatch):
    from jev_router.jev import get_jev_client, JevClient
    import os
    os.environ.pop("JEV_CLIENT", None)
    assert isinstance(get_jev_client({"jev": {"client": "stdlib"}}), JevClient)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/integration/test_cli.py -v -k "not live"`
Expected: PASS baseline (new assert lives in unit file; run `python -m pytest tests/unit/test_jev.py -v` to see FAIL before `run.py` wiring — factory already exists from T4 so this pins wiring, not factory)

- [ ] **Step 3: Write minimal implementation**

```python
# cli/run.py: replace `JevClient(...)` construction with:
from jev_router.jev import get_jev_client
client = get_jev_client(config, timeout_ms=cfg["jev"]["timeout_ms"], deadline_ms=cfg["jev"]["deadline_ms"], max_retries=cfg["jev"]["max_retries"])
```

```markdown
<!-- ARCHITECTURE.md §10 append -->
SDK transport is opt-in (`jev.client: sdk` / `JEV_CLIENT=sdk`, `pip install jev-router[typesafe]`); default `stdlib` preserves zero-deps.
<!-- fix stale §29 ref in AGENTS.md-adjacent docs if present -->
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest -v`
Expected: PASS (103 + new tests)

- [ ] **Step 5: Commit**

```bash
git add src/jev_router/cli/run.py ARCHITECTURE.md docs/quickstart.md tests/integration/test_cli.py
git commit -m "feat: wire SDK factory into run path and docs"
```

## Self-Review

- Spec coverage: §1 factory/interface → T1+T4; SDK shims → T2+T5; data-flow normalize → T3; error/privacy → T2–T5 wrappers; testing → each task's steps + T6 full suite. OpenAPI verification for live `prompt/scale` added as first step note in T5 (raw-dict passthrough + fail-open).
- Placeholders: none — every step has exact file paths, code blocks, run commands, commit messages.
- Type consistency: `ask(payload)->(decision|None, ms, reason|None)` in T1–T4; live `ask_jev()->dict|None` shape in T5 matches existing proxy consumers; `resolve_client_kind` signature reused in T4.
- Review Focus: each of the 5 lines has an owning test (missing-extra → T2/T4 factory test; endpoint precedence → T2 `_endpoint` + T4 config test; live raw-dict fallback → T5; log-level → wrapper code + parity test asserting no log lift; parity → T2/T3 tests).
