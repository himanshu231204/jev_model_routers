# AGENTS.md — JEV Model Router

Agent-agnostic model-routing layer for coding agents (Claude Code, Codex, OpenCode, DeepAgents, Hermes).
Flow: coding agent → adapter → normalized request → router → policy → model resolver → provider.

## Current state of this repo (read this first)

- **All phases are implemented.** Every package under `src/jev_router/` (`cli/`, `core/`,
  `contracts/`, `adapters/`, `providers/`, `jev/`, `transport/`, `state/`, `config/`,
  `observability/`, `security/`) has real code, not stubs — e.g. `core/router.py`,
  `core/policy.py`, `core/resolver.py`, `jev/client.py`, and full adapters for
  `claude_code`, `codex`, `opencode`, `hermes`, `deepagents`. Implement inside the existing
  files/packages, do not restructure or rename packages to suit yourself.
- **`tests/` exists and is populated** under `tests/unit/`, `tests/integration/`,
  `tests/contract/`, `tests/adapters/`, `tests/routing/`, `tests/fixtures/`
  (see `docs/08-project-structure.md`). `python -m pytest` passes (51 tests as of this
  writing). Add tests alongside any change per the testing rules below.
- **No CI workflows, linter, formatter, type-checker, pre-commit, or lockfile exist.** Do not
  invent tool commands or add tooling unless asked. Verification today = import check + pytest.
- **`ARCHITECTURE.md` (~223 lines, 15 sections) is the design source of truth.** `docs/01…14`
  are verbatim splits of its sections and say "do not edit here; propose changes against the
  source section" — never edit `docs/01`–`docs/14`; change `ARCHITECTURE.md` instead.
  `docs/00-quickstart.md` is a standalone integration guide, not a section split, and may be
  hand-edited directly to stay accurate to `src/`.
- `docs/README.md` and `docs/01`–`docs/14` are tracked, committed files, not local scratch —
  treat them like any other versioned doc. `.superpowers/`, `.tmp/`, `.agents/` are local/
  untracked work; leave those alone.
- **`jev/client.py` targets TypeSafe's real System One API**
  (`POST https://api.typesafe.ai/v1/systemone`), not a placeholder host. `JEV_API_KEY` holds a
  TypeSafe API key. `jev/questions.py` builds the `{model, state, questions}` request;
  `jev/normalize.py` parses the `{answers: {tier: {choice, confidence}}}` response.
- README's directory sketch and roadmap checkboxes lag behind the code (they were written
  pre-implementation and haven't been updated). Trust `src/` and `ARCHITECTURE.md` over
  README prose when they disagree.

## Commands

- Python **>= 3.11**, `src/` layout, setuptools build, package name `jev_router`.
- **Zero runtime dependencies (`dependencies = []`) — stdlib only.** Adding a dependency is a
  significant decision; justify it (ARCHITECTURE.md §29: dependency rules).
- Install: `pip install -e .` (exposes the `jev-router` console script →
  `jev_router.cli.main:main`, which dispatches to `run`/`agents`/`models`/`status`/
  `explain`/`doctor` subcommands).
- All tests: `python -m pytest`
- One file / one test: `python -m pytest tests/unit/test_policy.py` or
  `python -m pytest tests/unit/test_policy.py::test_name`
- Config used at runtime: `configs/default.yaml`, `configs/example.yaml`.

## Architecture and dependency direction

Packages under `src/jev_router/`: `cli/`, `core/`, `contracts/`, `adapters/`, `providers/`,
`jev/`, `transport/`, `state/`, `config/`, `observability/`, `security/`.

Dependency direction is one-way: **CLI → adapters → core → contracts**.
- `core/` imports `contracts/` only. Providers and transports are *injected*, never imported by
  policy/router code.
- Agent protocol knowledge (parsing, proxies, version quirks) → `adapters/<agent>/` only.
  Never `if agent == "claude":` in `core/`.
- Upstream model API knowledge (endpoints, auth, streaming) → `providers/`.
- HTTP/SSE/WS forwarding → `transport/`. Per-turn/session persistence → `state/`.
  Secrets/redaction → `security/`. Logging/metrics/explanations → `observability/`.
- Adding an agent = new `adapters/<foo>/` + fixtures + tests. It must not require touching the
  core router, policy, JEV auth, state, or registry.

## Routing invariants (must not regress)

- **JEV is the only routing authority.** `JEV_API_KEY` is read exclusively by `jev/client.py`;
  no other module may build JEV auth headers. Never hard-code, commit, or print the key.
  `core/classifier.py` must not grow into an independent LLM router.
- **One routing decision per fresh user turn.** Pin the selected model for the whole tool loop;
  tool results, continuations, telemetry, and title/summary calls bypass routing.
- **Explicit user model choice always wins** over automatic routing.
- **Fail open, but never silently:** missing key, timeout, 5xx, or malformed JEV response →
  fall back to current/default model and *record why* (current → agent default → configured
  fallback → clear error).
- **State is scoped `agent + session + turn`.** Sub-agent decisions must not overwrite the
  parent session's pinned model. No global `current_model`.
- Policy sits between JEV and execution: JEV output → policy (confidence thresholds, override,
  model availability, context/downgrade protection) → resolver → concrete model.
- Never log prompts, keys, auth headers, or raw responses by default (`configs/default.yaml`
  ships `privacy.log_prompts: false`, `send_repository_content: false` — keep those semantics).

## Configuration

- Precedence (implemented in `config/loader.py`): **CLI args > env vars > project config >
  user config > defaults**.
- `configs/default.yaml`: `jev.timeout_ms: 1500`, `deadline_ms: 3000`, `max_retries: 1`.
  Routing is on the interactive hot path — keep calls short; retry only within the deadline.
- Routing is disabled (passthrough) when `JEV_API_KEY` is absent — the CLI must report this
  clearly instead of crashing a running session.

## Testing rules

- pytest only; `pyproject.toml` `[tool.pytest.ini_options] testpaths = ["tests"]`.
- **Mock the JEV API in all default tests.** Live tests are opt-in: `JEV_LIVE_TESTS=1` plus
  `JEV_API_KEY` in the environment; never put a real key in fixtures.
- Adapter tests are fixture-driven (`tests/fixtures/`): capture sanitized upstream requests
  when a protocol changes, note the agent version, and assert expected routing behavior.
- Every non-trivial change to policy, resolution, overrides, fresh-turn detection, state
  isolation, or fallback needs a test — these are the pure-logic hot spots.

## Key contracts and modules

- `contracts/requests.py` — `NormalizedRequest` (agent, session, turn, prompt, current model,
  available models, context tokens, tools, explicit override, routing mode). Optional fields
  stay nullable; never invent data an adapter can't reliably provide.
- `contracts/models.py` — `ModelSpec` capability metadata (coding, reasoning, tool_use, context,
  speed, cost, context window, vision, availability, agent compatibility).
- `jev/schema.py` — `JEVDecision` (selected model/profile, confidence, task complexity,
  reasoning/tool signals, explanation). Normalize external JEV responses at this boundary only;
  raw provider/agent formats must not spread past it.
- `core/overrides.py` — explicit human model choice detection; consulted before JEV.
- `core/resolver.py` — picks a concrete model:
  `available ∩ agent-compatible ∩ provider-compatible ∩ policy-allowed`.
- `state/` — `memory.py` (in-process) and `sqlite.py` (persistent) behind `store.py`;
  holds `TurnState` (session, turn, selected model, selected_at, confidence, reason).
- `adapters/registry.py` / `providers/registry.py` — discovery points; adapters and providers
  register here instead of being wired into `core/` by hand.

## Common workflows

**Add a new agent adapter `foo`:**
1. Create `src/jev_router/adapters/foo/` with `adapter.py` (+ parser/proxy/config as needed).
2. Implement normalization into `NormalizedRequest`, fresh-turn detection, manual-override
   detection, and `apply_model` — reuse `jev/client.py` for JEV auth, never your own.
3. Register it in `adapters/registry.py`.
4. Add sanitized request/response fixtures + tests: fresh turn, tool continuation, manual
   model, auxiliary call, malformed request, unavailable model.
5. Do **not** modify `core/` to understand `foo`.

**Add a provider:** implement under `providers/`, register in `providers/registry.py`, add
`ModelSpec` entries, cover streaming + error semantics with tests. Providers never contain
routing policy and never learn *why* a model was chosen.

**Change routing behavior:** policy/resolution logic lives in `core/policy.py` +
`core/resolver.py` as pure, typed, deterministic functions with thresholds in config — not as
magic constants scattered through adapters. Update `ARCHITECTURE.md` alongside.

## Definition of done

- [ ] Code landed in the correct layer (see dependency direction above).
- [ ] Explicit overrides, fresh-turn pinning, and fail-open fallback still hold.
- [ ] No secrets or prompt content added to logs/errors.
- [ ] `python -m pytest` passes; new tests added.
- [ ] Behavior change reflected in `ARCHITECTURE.md` (not `docs/*`).

Full behavioral contract: `ARCHITECTURE.md`. Product/roadmap context: `README.md`.
