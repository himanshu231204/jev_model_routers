# JEV client: async conversion + exponential backoff

Status: approved design, pending spec review
Date: 2026-09-25
Scope: bounded-to-architectural (interface change ripples across the call chain)

## Problem

`JevClient.ask()` (`src/jev_router/jev/client.py`) retries exactly once on failure
(`max_retries=1`) with no delay between attempts — a failing or slow TypeSafe endpoint gets
hammered immediately instead of backing off. Separately, the router has no asyncio anywhere:
`Router.route()` and `JevClient.ask()` are fully synchronous, and the one HTTP attempt runs on a
manually managed `threading.Thread` joined with a wall-clock timeout (`client.py:21-45`) to work
around `urllib.request.urlopen`'s `timeout=` only bounding individual socket ops, not the whole
call.

`AGENTS.md` already flags that a live proxy (`transport/`) that would handle multiple concurrent
in-flight turns is designed for but not yet built. Converting the JEV call chain to `asyncio` now,
while adding the backoff, prepares that path: an event loop that awaits `asyncio.to_thread(...)`
per in-flight request stays free to service other requests, whereas today's per-call
`threading.Thread` has no such host to yield to.

## Goals

- Add exponential backoff between JEV retry attempts, clamped to the existing `deadline_ms`
  hard ceiling — never exceed the deadline invariant in `AGENTS.md`'s routing-invariants section.
- Convert the `JevClient.ask` → `Router.route` call chain to `async def`, bridged to the
  synchronous CLI entry point (`cli/run.py`) via one `asyncio.run()` call.
- Preserve every existing routing invariant: fail-open on `missing_api_key` /
  `deadline_exceeded` / `jev_error:*`, one routing decision per fresh turn, state pinning
  unchanged, zero runtime dependencies (stdlib `asyncio` only, no new package).
- Preserve the "abandon a hung request promptly" property `test_client_enforces_hard_wall_clock_deadline`
  asserts today.

## Non-goals

- No real non-blocking socket I/O (no `aiohttp`/`httpx` dependency). The blocking `urlopen` call
  still runs in a thread; only the *waiting* becomes cooperative via `asyncio.to_thread`.
- No live proxy / concurrent-request server in `transport/` — this spec only prepares the JEV
  call chain to be awaitable from one, it does not build the proxy itself.
- No change to `max_retries` default (stays `1`), `deadline_ms` default (stays `3000`), or the
  policy/resolver/adapter layers.
- No new test dependency (`pytest-asyncio` is explicitly not added — see Testing).

## Design

### Components touched

- **`jev/client.py`**
  - `_request_once` becomes `async def`, replacing the manual `threading.Thread` + `t.join(timeout)`
    pattern with `await asyncio.wait_for(asyncio.to_thread(<blocking urlopen call>), timeout=wall_clock_timeout)`.
    `asyncio.wait_for` raises `asyncio.TimeoutError` promptly when the timeout elapses without
    waiting for the underlying thread to finish — the thread keeps running in the background
    (same abandonment behavior as today's daemon thread; nothing changes about not blocking
    process exit, since `asyncio.to_thread` also uses daemon threads under the hood).
  - `ask()` becomes `async def ask(...)`. The retry loop gains a backoff sleep between attempts:
    `delay = min(0.1 * (2 ** attempt), remaining_deadline)`, `await asyncio.sleep(delay)` — only
    when another attempt will actually be made (not after the final allowed attempt), and never
    sleeping past the deadline.
  - No signature changes to `__init__` — `timeout_ms`/`deadline_ms`/`max_retries` stay the same
    constructor args.

- **`core/router.py`**
  - `route()` becomes `async def route(...)`, with `decision, latency_ms, error = await self.jev.ask(payload)`
    replacing the current synchronous call. Every other line is unchanged — the
    tool-continuation/override early-return paths don't touch `self.jev`, so they're unaffected in
    behavior, just now living inside an `async def`.

- **`cli/run.py`**
  - `run_run()` stays a synchronous `def` (it's the argparse-dispatched entry point called from
    `cli/main.py:main`, which must stay sync). The single line `decision = router.route(request)`
    becomes `decision = asyncio.run(router.route(request))`. Everything else — config loading,
    `adapter.launch_command`, `shutil.which`, `subprocess.run` — is untouched and stays fully
    synchronous, since none of it does I/O worth awaiting and `subprocess.run` must block until
    the launched agent process exits anyway.

- **Untouched:** `adapters/*`, `state/memory.py`, `core/policy.py`, `core/resolver.py`,
  `core/classifier.py`, `core/overrides.py`, `core/lifecycle.py`, `jev/questions.py`,
  `jev/normalize.py`, `jev/schema.py`, `config/loader.py`, `contracts/*`. None of these call or
  are called by anything becoming async.

### Data flow

Unchanged. `run_run` → `Router.route` → (classify → early-return, or) `JevClient.ask` → `Policy.evaluate`
→ `ModelResolver.resolve` → `store.pin` → `RoutingDecision`. The only new element in this flow is
the backoff sleep inside `JevClient.ask`'s retry loop, which is invisible to every caller above it
— `Router.route`'s contract (inputs/outputs/`RoutingDecision` shape) does not change, only that
callers must now `await` it.

### Error handling

No new failure modes. The three existing fail-open outcomes are preserved exactly:
- `missing_api_key` — headers are `None`, returned immediately, no backoff involved.
- `deadline_exceeded` — returned when `remaining <= 0` at loop-top, same as today.
- `jev_error:{ExceptionTypeName}` — returned when retries are exhausted or the deadline is hit
  mid-retry, same as today, just with a bounded sleep between attempts instead of an immediate
  re-attempt.

The backoff delay is computed as `min(0.1 * 2**attempt, remaining_deadline)` specifically so it
can never itself cause a deadline overrun — worst case, the sleep consumes exactly the remaining
budget and the next loop iteration's `remaining <= 0` check returns `deadline_exceeded` as it does
today.

### Testing

Three existing test files call `.ask()` / construct `Router` and call `.route()` synchronously and
must be updated — grepped call sites:

- `tests/unit/test_jev.py`: `test_client_missing_key_returns_error`,
  `test_client_enforces_hard_wall_clock_deadline` — both call `c.ask(...)` directly.
- `tests/routing/test_router.py`: `FakeJev.ask` (sync method) and both tests calling `r.route(_req())`.
- `tests/integration/test_cli.py`: three tests monkeypatching `JevClient.ask` with a sync `lambda`.

Rather than add `pytest-asyncio` as a new test-only dependency, every test function stays a plain
`def` (not `async def`) and drives the coroutine with `asyncio.run(...)` inside the test body —
e.g. `dec, ms, err = asyncio.run(c.ask({"prompt": "hi"}))`. `FakeJev.ask` and the `JevClient.ask`
monkeypatch lambdas become `async def` functions (or `async def` closures) instead of plain
functions — monkeypatching an attribute with an async function works identically to today's sync
version from `setattr`'s perspective. No `pyproject.toml` changes.

`test_client_enforces_hard_wall_clock_deadline` in particular needs its mock verified still valid:
the monkeypatched `slow_urlopen` is still called from inside `asyncio.to_thread`, so the blocking
`time.sleep(2)` still runs in a worker thread; `asyncio.wait_for(..., timeout=0.1)` around it must
still return promptly (assertion: `wall_clock < 1.0`) without waiting for that thread — this is the
one behavior this spec must not regress, so this test is the primary regression guard for the
whole conversion and should be run first when implementing.

New test to add: an exponential-backoff assertion — mock `asyncio.sleep` (or measure wall-clock
across a deliberately-failing `urlopen` with `max_retries=1`) and assert the observed delay is
`>= 0.1s` and `< remaining_deadline`, i.e. backoff actually happened and stayed inside budget.

## Open questions

None — all prior clarifying questions (async motivation, backoff parameters, test dependency
stance) were resolved during brainstorming and are reflected above as decisions, not options.
