# AGENTS.md — JEV Model Router

Per-turn model routing for Claude Code (and OpenAI Codex), decided by TypeSafe's Jev.
Flow: Claude Code → local proxy (`jev_router_live`) → Jev picks a model for each fresh turn →
policy → request rewritten to that model → Anthropic → streamed back unchanged.

## Current state of this repo (read this first)

- **One package: `src/jev_router_live/`.** The earlier session-start router (`src/jev_router/`,
  its adapters/core/contracts, `configs/`, the `jev-router` command and their tests) was removed;
  it lives only in git history. Don't reintroduce a second router, Jev client or proxy.
- **`ARCHITECTURE.md` is the design source of truth — read it directly.** `docs/quickstart.md`
  is the user guide; `src/jev_router_live/README.md` is the package guide. Keep development
  scratch (plans, specs, notes) out of the repository.
- **Non-Python files the package needs at runtime live inside `src/jev_router_live/`** and are
  listed in `pyproject.toml` `[tool.setuptools.package-data]` (today: the Codex
  `skills/codex/jev-explain/SKILL.md`). Anything at the repo root is not installed.
- **Tests:** `tests/live/` (unit + proxy-integration, Jev mocked) and
  `tests/live/test_live_jev_api.py` (real Jev, opt-in). `python -m pytest` passes (106 tests,
  3 skipped live-API tests, as of this writing). CI (`.github/workflows/ci.yml`) installs the `typesafe` extra and runs pytest on
  Python 3.11 and 3.12 for every PR. There is no linter, formatter, type-checker or lockfile;
  don't invent tool commands.
- **Verified against real Claude Code 2.1.282** (`jev-claude`, interactive and `-p`), with Jev
  answered by `scripts/fake_jev.py` because the real API wasn't reachable from the test
  environment. The request/response schema matches TypeSafe's quickstart
  (`docs.typesafe.ai/introduction/quickstart`). The real-API test still needs to be run with a
  real key.

## Commands

- Python **>= 3.11**, `src/` layout, setuptools. Published to PyPI as **`jev-model-router`**
  and as a Docker image at **`ghcr.io/himanshu231204/jev_model_routers`** (`Dockerfile`,
  built from source, bundles the Claude Code / Codex CLIs); the version lives only in
  `src/jev_router_live/version.py`. Releases are cut by pushing a `v*` tag — follow
  `RELEASE.md` (bump version + `CHANGELOG.md` section, then tag; both publishes run off the
  same tag).
- **Zero runtime dependencies (`dependencies = []`), stdlib only.** `pytest` is the `test`
  extra; `typesafe-sdk` is the optional `typesafe` extra used only with `JEV_CLIENT=sdk`.
- Install: `pip install -e ".[test]"` → console scripts `jev-claude`, `jev-codex`,
  `jev-explain`.
- All tests: `python -m pytest -q` (install `.[test,typesafe]` so the SDK-client tests run too); one test: `python -m pytest tests/live/test_live_policy.py::name`.
- Real Jev: `JEV_LIVE_TESTS=1 TYPESAFE_API_KEY=… python -m pytest tests/live/test_live_jev_api.py -s`.
- Real Claude Code without Jev access: `python scripts/fake_jev.py 8765`, then
  `JEV_ENDPOINT=http://127.0.0.1:8765/v1/systemone TYPESAFE_API_KEY=local jev-claude -p "…"`.

## Module boundaries

- `config.py` — every routing knob (tiers + verified static model ids, thresholds, override
  phrases, Jev questions). Change thresholds here, nowhere else.
- `policy.py` — `decide()`, pure and total. No I/O, no HTTP.
- `stdlib_router.py` — **the** Jev client (`sdk_router.py` is the opt-in alternative, dispatched
  by `router.ask_jev`). It knows nothing about Claude Code. Don't add another client.
- `proxy.py` — the only module that understands the Anthropic wire format: fresh-turn
  detection, conversation pinning, model catalog, request rewriting, streaming relay.
- `codex_proxy.py` — the Codex (Responses API) equivalent; shares the client and policy.
- `status.py` / `explain.py` / `bin/jev_statusline.py` — decision file and its readers.
- `bin/jev_claude.py` — launcher: environment for the `/model` "JEV Router" row, proxy
  lifecycle, restores the saved default model on exit.

## Routing invariants (must not regress)

- **Auth is `TYPESAFE_API_KEY` only** (TypeSafe's documented name), read via
  `config.api_key()`. Credential variable names appear only in `config.py` (a test enforces
  it). The old name `JEV_API_KEY` is never read — only detected to tell the user to rename it.
  Never hard-code, commit, print or log the key.
- **Jev is called once per fresh user turn.** Tool continuations, resent copies of the same
  turn (same prompt + same conversation length; Claude Code 2.1.282 sends a turn's first
  request twice), `[SUGGESTION MODE:` prompt-suggestion requests and auxiliary calls never call
  Jev; they reuse a pinned model.
- **The conversation key** is the session id + the user-authored first-message text (injected
  `<system-reminder>` blocks stripped). Sub-agents get their own key; nothing is global.
- **Explicit choice wins.** A non-sentinel model passes through untouched; a prompt override
  ("use opus") beats Jev.
- **Jev recommends, `decide()` decides.** Low confidence never downgrades; cache protection
  applies only after the first decision; unavailable/unknown models are never used.
- **Fail open, visibly.** No key, timeout, 5xx, 4xx, malformed answer or crash → a real model
  (never the sentinel), within the 3 s Jev deadline, with a log line. Retry only
  timeouts/network/5xx, once.
- **Rewrite minimally.** Only `model` and fields the chosen model cannot accept.
- **Stream, don't buffer** (except `/v1/models`). Keep framing valid (never
  `Transfer-Encoding` next to `Content-Length`). Only client-side resets are quiet; upstream
  failures are logged.
- **Privacy.** The decision log (`record()`) gets safe metadata only; prompts appear only in
  the owner-only status file and under `JEV_DEBUG`. Files under `<tempdir>/jev-claude/` are
  written only via `status.private_dir()` / `write_private()`.
- **Don't widen Claude Code's permissions** (no `--add-dir`, no settings beyond the status line).

## Testing rules

- pytest only; mock Jev in all default tests (`route=` injection into `start_proxy`, or
  monkeypatching `stdlib_router._post`). Never put a real key in fixtures.
- Proxy tests run against a local fake Anthropic upstream (see
  `tests/live/test_live_hardening.py`); model new Claude Code request shapes on captured real
  traffic and note the Claude Code version.
- `tests/live/conftest.py` isolates `~/.jev-claude.log` and `<tempdir>/jev-claude`; keep new
  tests inside `tests/live/` so they inherit it.
- Every non-trivial change to policy, turn detection, pinning, catalog, rewriting, streaming,
  fallback or file handling needs a test.

## Definition of done

- [ ] Change lives in the right module (boundaries above); no second client/router/proxy.
- [ ] Routing invariants above still hold.
- [ ] No secrets or prompt content added to logs/errors.
- [ ] `python -m pytest` passes; new tests added.
- [ ] Behavior change reflected in `ARCHITECTURE.md`; user-visible change in `README.md` /
      `docs/quickstart.md`.
- [ ] For changes to how Claude Code traffic is handled: verified with a real `jev-claude` run.
