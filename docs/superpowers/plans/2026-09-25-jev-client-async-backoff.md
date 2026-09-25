# JEV Client Async Conversion + Exponential Backoff Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert the `JevClient.ask` → `Router.route` call chain to `async def`, add exponential backoff between JEV retry attempts, and bridge the synchronous CLI entry point with a single `asyncio.run()` call — with zero new dependencies and zero regressions to existing routing invariants.

**Architecture:** `JevClient._request_once`/`ask` and `Router.route` become `async def`. The blocking `urllib.request.urlopen` call runs via `asyncio.to_thread`, wrapped in `asyncio.wait_for` to preserve today's "abandon a hung request at the wall-clock deadline" behavior. `cli/run.py`'s `run_run()` stays a synchronous `def` (it's the argparse-dispatched entry point) and gets exactly one `asyncio.run(router.route(request))` bridge point; nothing else in the CLI, adapters, state, policy, or resolver layers changes.

**Tech Stack:** Python 3.11 stdlib only — `asyncio`, `urllib.request` (already used), `pytest` (already a test dep; no `pytest-asyncio` added).

**Spec:** `docs/superpowers/specs/2026-09-25-jev-client-async-backoff-design.md`

## Global Constraints

- Python **>= 3.11**, stdlib only — no new runtime or test dependencies (spec: Goals, Non-goals).
- `deadline_ms` (default 3000) is a hard ceiling — no sleep or retry may ever push a call past it (spec: Error handling).
- `max_retries` default stays `1`; backoff base is `0.1s` (100ms) doubling per retry, computed as `delay = min(0.1 * 2**attempt, remaining_deadline)` where `attempt` is the 0-indexed retry count before increment (spec: Design → `jev/client.py`).
- Every existing fail-open reason string must be preserved byte-for-byte: `"missing_api_key"`, `"deadline_exceeded"`, `f"jev_error: {type(err).__name__}"` (note the space after the colon) (spec: Error handling).
- Exactly one `asyncio.run()` call site in the whole codebase, in `cli/run.py`'s `run_run()` (spec: Design → `cli/run.py`).
- No `pytest-asyncio`: every test stays a plain `def`, driving coroutines with `asyncio.run(...)` inside the test body (spec: Testing).

---

### Task 1: Async `JevClient` with backoff + async `Router.route`

**Files:**
- Modify: `src/jev_router/jev/client.py` (full rewrite of `_request_once` and `ask`)
- Modify: `src/jev_router/core/router.py:26` (`route` signature) and `:53` (the `self.jev.ask(payload)` call)
- Test: `tests/unit/test_jev.py` (update 2 existing tests, add 1 new test)
- Test: `tests/routing/test_router.py` (update `FakeJev.ask` and both call sites)

**Interfaces:**
- Consumes: nothing from other tasks (this is the foundation task).
- Produces: `JevClient.ask(payload: dict) -> Awaitable[tuple[JEVDecision | None, int, str | None]]` (now a coroutine function — same return shape as before, just must be awaited). `Router.route(request: NormalizedRequest) -> Awaitable[RoutingDecision]` (now a coroutine function — same return shape as before, just must be awaited). Task 2 relies on both of these being coroutine functions.

- [ ] **Step 1: Update `tests/unit/test_jev.py`'s two existing tests to await via `asyncio.run`, and add a new backoff test**

Replace the full contents of `tests/unit/test_jev.py` with:

```python
import asyncio
import os
from jev_router.jev.normalize import normalize_jev_payload
from jev_router.jev.questions import build_jev_payload
from jev_router.contracts.requests import NormalizedRequest

def test_normalize_clamps_confidence():
    raw = {"answers": {"tier": {"type": "choice", "choice": "strong", "confidence": 9}}}
    d = normalize_jev_payload(raw, 10)
    assert 0.0 <= d.confidence <= 1.0 and d.requested_tier == "strong"

def test_normalize_unknown_choice_is_none():
    raw = {"answers": {"tier": {"type": "choice", "choice": "bogus", "confidence": 0.5}}}
    d = normalize_jev_payload(raw, 10)
    assert d.requested_tier is None

def test_payload_minimal_by_default():
    r = NormalizedRequest(request_id="r", agent="a", session_id="s", conversation_id="c",
                          turn_id="t", prompt="secret prompt", messages=[],
                          available_models=["m"], tools=[], tool_count=0, metadata={})
    p = build_jev_payload(r, {"send_repository_content": False})
    assert p["model"] and p["questions"]["tier"]["type"] == "choice"
    assert p["state"]["prompt"] == "secret prompt" and "repository" not in p["state"]

def test_payload_includes_repository_when_enabled():
    from jev_router.contracts.requests import RepositoryContext
    r = NormalizedRequest(request_id="r", agent="a", session_id="s", conversation_id="c",
                          turn_id="t", prompt="p", messages=[], available_models=["m"],
                          tools=[], tool_count=0, metadata={},
                          repository=RepositoryContext(language=["python"], project_type="lib"))
    p = build_jev_payload(r, {"send_repository_content": True})
    assert p["state"]["repository"] == {"language": ["python"], "project_type": "lib"}

def test_client_missing_key_returns_error():
    from jev_router.jev.client import JevClient
    os.environ.pop("TYPESAFE_API_KEY", None)
    c = JevClient(timeout_ms=100, deadline_ms=200, max_retries=0)
    dec, ms, err = asyncio.run(c.ask({"prompt": "hi"}))
    assert dec is None and err is not None

def test_client_enforces_hard_wall_clock_deadline(monkeypatch):
    """urlopen's own `timeout` only bounds individual socket ops, not the whole call -- a
    slow-but-not-individually-timed-out request must still be cut off at deadline_ms."""
    import time
    import jev_router.jev.client as client_mod

    def slow_urlopen(req, timeout=None):
        time.sleep(2)  # far longer than the deadline below
        raise AssertionError("should have been abandoned before completing")

    monkeypatch.setattr(client_mod.urllib.request, "urlopen", slow_urlopen)
    monkeypatch.setenv("TYPESAFE_API_KEY", "test-key")
    c = client_mod.JevClient(timeout_ms=5000, deadline_ms=100, max_retries=0)
    start = time.time()
    dec, ms, err = asyncio.run(c.ask({"prompt": "hi"}))
    wall_clock = time.time() - start
    assert dec is None and err is not None
    assert wall_clock < 1.0  # returned promptly despite the 2s-sleeping mock

def test_client_backs_off_before_retry(monkeypatch):
    """The one retry (max_retries=1) must wait ~100ms before firing again, not retry
    instantly -- and the wait must never push the call past deadline_ms."""
    import time
    import jev_router.jev.client as client_mod

    def failing_urlopen(req, timeout=None):
        raise OSError("connection refused")

    monkeypatch.setattr(client_mod.urllib.request, "urlopen", failing_urlopen)
    monkeypatch.setenv("TYPESAFE_API_KEY", "test-key")
    c = client_mod.JevClient(timeout_ms=500, deadline_ms=2000, max_retries=1)
    start = time.time()
    dec, ms, err = asyncio.run(c.ask({"prompt": "hi"}))
    wall_clock = time.time() - start
    assert dec is None and err is not None
    assert wall_clock >= 0.1  # the backoff delay actually happened
    assert wall_clock < 2.0  # stayed within the deadline
```

- [ ] **Step 2: Run the updated test file to confirm it fails (client is still sync)**

Run: `python -m pytest tests/unit/test_jev.py -v`
Expected: `test_client_missing_key_returns_error`, `test_client_enforces_hard_wall_clock_deadline`, and `test_client_backs_off_before_retry` all FAIL (the first two because `asyncio.run()` is being called on a plain tuple, not a coroutine — `TypeError: An asyncio.Future, a coroutine or an awaitable is required`; the third because `JevClient` doesn't exist yet in a way that produces backoff/`asyncio.run` fails the same way). The other 4 tests in the file (normalize/payload) should still PASS.

- [ ] **Step 3: Rewrite `src/jev_router/jev/client.py` to be async with backoff**

Replace the full contents of `src/jev_router/jev/client.py` with:

```python
"""JEV decision client; sole reader of TYPESAFE_API_KEY. Stdlib urllib with timeout/deadline."""
from __future__ import annotations
import asyncio, json, os, time, urllib.request
from jev_router.jev.normalize import normalize_jev_payload
from jev_router.jev.schema import JEVDecision

_ENDPOINT = os.environ.get("JEV_ENDPOINT", "https://api.typesafe.ai/v1/systemone")

class JevClient:
    def __init__(self, timeout_ms: int = 1500, deadline_ms: int = 3000, max_retries: int = 1):
        self.timeout_s = timeout_ms / 1000.0
        self.deadline_s = deadline_ms / 1000.0
        self.max_retries = max_retries

    def _headers(self) -> dict | None:
        key = os.environ.get("TYPESAFE_API_KEY")
        if not key:
            return None
        return {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}

    async def _request_once(self, payload: dict, headers: dict, wall_clock_timeout: float):
        """Run one HTTP attempt in a worker thread, bounded by an actual wall-clock deadline.

        urlopen's own `timeout` only bounds individual socket operations (connect, each
        read) -- a request whose DNS/connect/TLS/read steps are each fast but add up can run
        far longer than that. `asyncio.wait_for` enforces the real wall-clock deadline and
        returns promptly even if the underlying thread is still stuck -- `asyncio.to_thread`
        runs on the default executor's daemon threads, so an abandoned one never blocks
        process exit, same as the manually managed daemon thread this replaced.
        """
        def blocking_call():
            req = urllib.request.Request(_ENDPOINT, data=json.dumps(payload).encode(),
                                         headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=self.timeout_s) as resp:
                return json.loads(resp.read().decode() or "{}")
        try:
            raw = await asyncio.wait_for(asyncio.to_thread(blocking_call), timeout=wall_clock_timeout)
            return raw, None
        except asyncio.TimeoutError:
            return None, TimeoutError("wall_clock_deadline_exceeded")
        except Exception as e:
            return None, e

    async def ask(self, payload: dict) -> tuple[JEVDecision | None, int, str | None]:
        headers = self._headers()
        if headers is None:
            return None, 0, "missing_api_key"
        start = time.time()
        attempt = 0
        while True:
            remaining = self.deadline_s - (time.time() - start)
            if remaining <= 0:
                return None, int((time.time() - start) * 1000), "deadline_exceeded"
            raw, err = await self._request_once(payload, headers, remaining)
            if err is None:
                ms = int((time.time() - start) * 1000)
                return normalize_jev_payload(raw, ms), ms, None
            if attempt >= self.max_retries:
                return None, int((time.time() - start) * 1000), f"jev_error: {type(err).__name__}"
            remaining = self.deadline_s - (time.time() - start)
            if remaining <= 0:
                return None, int((time.time() - start) * 1000), f"jev_error: {type(err).__name__}"
            delay = min(0.1 * (2 ** attempt), remaining)
            await asyncio.sleep(delay)
            attempt += 1
```

- [ ] **Step 4: Run `tests/unit/test_jev.py` again to confirm the client tests now pass (router tests still pending Task 1 Step 5-7)**

Run: `python -m pytest tests/unit/test_jev.py -v`
Expected: all 7 tests PASS.

- [ ] **Step 5: Update `tests/routing/test_router.py` to use an async `FakeJev` and `asyncio.run`**

Replace the full contents of `tests/routing/test_router.py` with:

```python
import asyncio
from jev_router.core.router import Router
from jev_router.contracts.requests import NormalizedRequest
from jev_router.state.memory import MemoryStore

class FakeJev:
    async def ask(self, payload):
        from jev_router.jev.schema import JEVDecision
        return JEVDecision(requested_tier="strong", confidence=0.9), 5, None

def _req(**kw):
    base = dict(request_id="r1", agent="claude_code", session_id="s", conversation_id="c",
                turn_id="t1", prompt="hard refactor", messages=[], current_model="a/fast",
                available_models=["a/fast", "a/strong"], tools=[], tool_count=0,
                context_tokens=100, max_context_tokens=100000, metadata={})
    base.update(kw)
    return NormalizedRequest(**base)

def test_routes_and_pins_tool_loop():
    from jev_router.contracts.models import ModelSpec
    r = Router(jev_client=FakeJev(), store=MemoryStore(),
               candidates=[ModelSpec(id="a/fast", provider="a", tier="fast"),
                           ModelSpec(id="a/strong", provider="a", tier="strong")], privacy={})
    d1 = asyncio.run(r.route(_req()))
    assert d1.final_model == "a/strong"
    d2 = asyncio.run(r.route(_req(is_new_turn=False, metadata={"tool_result": True})))
    assert d2.final_model == "a/strong" and not d2.changed

def test_core_imports_only_contracts():
    import ast, pathlib
    tree = ast.parse(pathlib.Path("src/jev_router/core/router.py").read_text())
    mods = [n.module or "" for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)]
    assert not any(m.startswith("jev_router.adapters") or m.startswith("jev_router.providers") for m in mods)

def test_empty_candidates_no_current_model_fails_open():
    # Fail-open invariant: resolver's terminal ValueError must never propagate;
    # router returns a fallback decision with reason "no_candidates" instead.
    r = Router(jev_client=FakeJev(), store=MemoryStore(), candidates=[], privacy={})
    d = asyncio.run(r.route(_req(current_model=None, available_models=[])))
    assert d.reason == "no_candidates" and d.fallback and d.final_model == ""
```

- [ ] **Step 6: Run the updated test file to confirm it fails (`Router.route` is still sync)**

Run: `python -m pytest tests/routing/test_router.py -v`
Expected: `test_routes_and_pins_tool_loop` and `test_empty_candidates_no_current_model_fails_open` FAIL with `TypeError: An asyncio.Future, a coroutine or an awaitable is required` (since `r.route(...)` currently returns a `RoutingDecision`, not a coroutine, and `asyncio.run()` rejects it). `test_core_imports_only_contracts` should still PASS (it's pure static analysis).

- [ ] **Step 7: Make `Router.route` async in `src/jev_router/core/router.py`**

In `src/jev_router/core/router.py`, change line 26 from:

```python
    def route(self, request: NormalizedRequest) -> RoutingDecision:
```

to:

```python
    async def route(self, request: NormalizedRequest) -> RoutingDecision:
```

And change line 53 from:

```python
        decision, latency_ms, error = self.jev.ask(payload)
```

to:

```python
        decision, latency_ms, error = await self.jev.ask(payload)
```

- [ ] **Step 8: Run both test files to confirm everything passes**

Run: `python -m pytest tests/unit/test_jev.py tests/routing/test_router.py -v`
Expected: all tests PASS (7 in `test_jev.py`, 3 in `test_router.py`).

- [ ] **Step 9: Commit**

```bash
git add src/jev_router/jev/client.py src/jev_router/core/router.py tests/unit/test_jev.py tests/routing/test_router.py
git commit -m "feat: make JevClient.ask and Router.route async, add exponential backoff

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 2: Bridge the CLI entry point + update integration tests

**Files:**
- Modify: `src/jev_router/cli/run.py:64`
- Test: `tests/integration/test_cli.py` (update 4 tests: 3 monkeypatch `JevClient.ask` with async functions, 1 spy wraps `Router.route` async)

**Interfaces:**
- Consumes: `JevClient.ask` and `Router.route` as coroutine functions (from Task 1).
- Produces: `run_run(args: dict) -> int` — unchanged signature and return type; this is the last task, nothing downstream depends on new interfaces from this task.

- [ ] **Step 1: Update the 4 affected tests in `tests/integration/test_cli.py`**

In `tests/integration/test_cli.py`, add `import asyncio` at the top of the file (after the existing `from jev_router.cli.main import build_parser` line, add `import asyncio` above it or anywhere before first use — place it as the first line of the file).

Replace `test_run_passes_prompt_into_routing_request` with:

```python
def test_run_passes_prompt_into_routing_request(monkeypatch):
    import shutil, subprocess
    from jev_router.core.router import Router
    from jev_router.cli.run import run_run
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    monkeypatch.setattr(shutil, "which", lambda name: f"/resolved/{name}")
    monkeypatch.setattr(subprocess, "run", lambda cmd: type("R", (), {"returncode": 0})())
    seen = {}
    original_route = Router.route
    async def spy_route(self, request):
        seen["prompt"] = request.prompt
        return await original_route(self, request)
    monkeypatch.setattr(Router, "route", spy_route)
    run_run({"agent": "claude_code", "prompt": "add input validation to the login form"})
    assert seen["prompt"] == "add input validation to the login form"
```

Replace `test_run_resolves_fast_tier_to_fable_not_opus` with:

```python
def test_run_resolves_fast_tier_to_fable_not_opus(monkeypatch):
    """Every JEV tier ("fast", "balanced", "strong") must have a real matching candidate for
    claude_code -- a missing tier previously made the resolver's fallback always escalate to
    the highest-capability candidate (opus) instead of respecting a "fast" recommendation."""
    import shutil, subprocess
    from jev_router.jev.client import JevClient
    from jev_router.jev.schema import JEVDecision
    from jev_router.cli.run import run_run
    monkeypatch.setenv("TYPESAFE_API_KEY", "test-key")
    monkeypatch.setattr(shutil, "which", lambda name: f"/resolved/{name}")
    calls = []
    monkeypatch.setattr(subprocess, "run", lambda cmd: calls.append(cmd) or type("R", (), {"returncode": 0})())
    async def fake_ask(self, payload):
        return JEVDecision(requested_tier="fast", confidence=0.95), 10, None
    monkeypatch.setattr(JevClient, "ask", fake_ask)
    run_run({"agent": "claude_code", "prompt": "fix a typo in the README"})
    assert calls[0] == ["/resolved/claude", "--model", "fable"]
```

Replace `test_run_resolves_strong_tier_to_opus_not_sonnet` with:

```python
def test_run_resolves_strong_tier_to_opus_not_sonnet(monkeypatch):
    """A JEV "strong" recommendation must actually reach the opus candidate for claude_code,
    not silently fall back to whichever catalog entry happens to be first."""
    import shutil, subprocess
    from jev_router.jev.client import JevClient
    from jev_router.jev.schema import JEVDecision
    from jev_router.cli.run import run_run
    monkeypatch.setenv("TYPESAFE_API_KEY", "test-key")
    monkeypatch.setattr(shutil, "which", lambda name: f"/resolved/{name}")
    calls = []
    monkeypatch.setattr(subprocess, "run", lambda cmd: calls.append(cmd) or type("R", (), {"returncode": 0})())
    async def fake_ask(self, payload):
        return JEVDecision(requested_tier="strong", confidence=0.9), 10, None
    monkeypatch.setattr(JevClient, "ask", fake_ask)
    run_run({"agent": "claude_code", "prompt": "design a distributed consensus algorithm"})
    assert calls[0] == ["/resolved/claude", "--model", "opus"]
```

Replace `test_run_never_resolves_openai_candidate_for_claude_code` with:

```python
def test_run_never_resolves_openai_candidate_for_claude_code(monkeypatch):
    """Even if JEV recommends "strong" and openai/coding-strong ties on capability lookup,
    compatible_agents must keep it out of a claude_code launch."""
    import shutil, subprocess
    from jev_router.jev.client import JevClient
    from jev_router.jev.schema import JEVDecision
    from jev_router.cli.run import run_run
    monkeypatch.setenv("TYPESAFE_API_KEY", "test-key")
    monkeypatch.setattr(shutil, "which", lambda name: f"/resolved/{name}")
    calls = []
    monkeypatch.setattr(subprocess, "run", lambda cmd: calls.append(cmd) or type("R", (), {"returncode": 0})())
    async def fake_ask(self, payload):
        return JEVDecision(requested_tier="strong", confidence=0.9), 10, None
    monkeypatch.setattr(JevClient, "ask", fake_ask)
    run_run({"agent": "claude_code", "prompt": "anything"})
    assert calls[0][2] != "openai/coding-strong"
```

- [ ] **Step 2: Run the integration test file to confirm the 4 updated tests fail (CLI doesn't bridge async yet)**

Run: `python -m pytest tests/integration/test_cli.py -v`
Expected: `test_run_passes_prompt_into_routing_request`, `test_run_resolves_fast_tier_to_fable_not_opus`, `test_run_resolves_strong_tier_to_opus_not_sonnet`, and `test_run_never_resolves_openai_candidate_for_claude_code` all FAIL with a `TypeError` from `run_run` trying to unpack/use a coroutine object as a `RoutingDecision` (since `Router.route` is async as of Task 1 but `run_run` still calls it synchronously). The other tests in the file (`test_run_launches_subprocess_with_routed_model`, `test_run_reports_missing_binary_not_crash`, `test_run_deepagents_reports_error_not_crash`, etc.) should also FAIL the same way, since they all go through `run_run` → `router.route(...)`.

- [ ] **Step 3: Bridge `run_run` with `asyncio.run` in `src/jev_router/cli/run.py`**

In `src/jev_router/cli/run.py`, add `asyncio` to the imports — change line 3 from:

```python
import shutil, subprocess
```

to:

```python
import asyncio, shutil, subprocess
```

Then change line 64 from:

```python
    decision = router.route(request)
```

to:

```python
    decision = asyncio.run(router.route(request))
```

- [ ] **Step 4: Run the full test suite to confirm everything passes**

Run: `python -m pytest -v`
Expected: all tests PASS (no failures, no errors). This is the full regression check — it covers every test file in the repo, not just the ones touched by this plan.

- [ ] **Step 5: Commit**

```bash
git add src/jev_router/cli/run.py tests/integration/test_cli.py
git commit -m "feat: bridge async routing into the sync CLI entry point via asyncio.run

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```
