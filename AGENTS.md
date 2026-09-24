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
  (see `ARCHITECTURE.md` §9). `tests/live/` covers `jev_router_live` (§16) the same way.
  `python -m pytest` passes (103 tests as of this writing). Add
  tests alongside any change per the testing rules below.
- **No CI workflows, linter, formatter, type-checker, pre-commit, or lockfile exist.** Do not
  invent tool commands or add tooling unless asked. Verification today = import check + pytest.
- **`ARCHITECTURE.md` (~204 lines, 15 sections) is the design source of truth — read it
  directly.** `docs/` holds only `docs/README.md` (points here) and `docs/quickstart.md`
  (integration guide, hand-maintained, may be edited directly to stay accurate to `src/`). The
  old one-file-per-section split (`docs/01`–`docs/14`) and five empty placeholder directories
  were removed as unnecessary duplication. All of `docs/` is tracked and committed — it is not
  local scratch. Only `.superpowers/`, `.tmp/`, and `.agents/` are local/untracked work; leave
  those alone.
- **The JEV client is wired to TypeSafe's real System One API**, not a placeholder. `jev/
  client.py` calls `POST https://api.typesafe.ai/v1/systemone` with `TYPESAFE_API_KEY` as the
  bearer token — the same env var name TypeSafe's own SDK reads by default, even though this
  router calls the raw HTTP API directly via stdlib `urllib` (zero runtime deps) rather than
  depending on the SDK. `jev/questions.py` builds the `{model, state, questions}` request
  (a single `"tier"` choice question); `jev/normalize.py` parses the
  `{answers: {tier: {choice, confidence}}}` response. Both shapes are verified against
  TypeSafe's quickstart (`docs.typesafe.ai/introduction/quickstart`) and SDK docs
  (`docs.typesafe.ai/sdk/python`, `/sdk/javascript`).
- **`jev-router run --agent <name>` actually launches the agent now**, via
  `AgentAdapter.launch_command(model)` + `subprocess.run`, after one JEV routing decision at
  session start. This is session-start routing only, not per-turn — `jev_router`'s own
  `transport/` only sends outbound; nothing listens for mid-session requests. Per-turn routing
  via a live local proxy exists as a separate package, `src/jev_router_live/` (`jev-claude` /
  `jev-codex` / `jev-explain`; see `ARCHITECTURE.md` §16 and `src/jev_router_live/README.md`) —
  it does not share code with `jev_router` and is not part of the adapter/core/contracts
  pipeline described above. `launch_command` was verified against each real installed CLI's
  `--help`, not
  guessed: `claude --model <m>` and `hermes chat --model <m>` are correct; `codex --model <m>`
  is unverified (binary not available to test against). `opencode.launch_command` and
  `deepagents.launch_command` both raise `NotImplementedError` rather than emit a broken
  command — opencode's interactive CLI has no top-level `--model` flag, and deepagents has no
  CLI binary at all. `HermesAdapter.detect()` now uses `shutil.which("hermes")` like every
  other adapter (it was hardcoded to always return `False`). The Reverse Proxy and SDK Adapter
  integration strategies in `docs/quickstart.md` remain unimplemented.
- **`cli/run.py` resolves `launch_command`'s argv[0] via `shutil.which()` before calling
  `subprocess.run`.** A bare `"claude"` fails Windows's `CreateProcess` even when it's on PATH
  and `shutil.which` finds it — the real executable there is a `.CMD` shim (e.g. `claude.CMD`)
  and the extensionless name doesn't resolve the same way `cmd.exe` resolves it. Passing the
  resolved full path fixes it on both Windows and POSIX. Verified live: `jev-router run --agent
  claude_code` now actually launches `claude` (previously: `FileNotFoundError` dumped as a raw
  traceback). Missing-binary and launch-failure cases print a clean one-line error and return 1
  instead of crashing.
- **`jev-router run` now takes `--prompt`/`-p`.** Without it, JEV is asked to route an empty
  string and — live-verified — reliably returns confidence around 0.27 (below the `low`
  threshold), so `core/policy.py` falls back (`reason=low_confidence_keep_current`) instead of
  routing. The same real prompt live-verified confidence 0.97 for the same tier. Always pass
  `--prompt` for a real routing decision; omitting it is a deliberate no-signal passthrough,
  not a bug.
- **`ClaudeCodeAdapter.launch_command` now translates catalog ids to real Claude Code
  aliases** (`_MODEL_ALIASES` in `adapters/claude_code/adapter.py`: `anthropic/claude-sonnet`
  → `sonnet`, `anthropic/claude-opus` → `opus`), fixing the "isn't described by this version's
  model catalog" error `claude --model anthropic/claude-sonnet` produced before. Only these two
  ids are mapped — `openai/coding-strong` and any other catalog id still pass through
  unchanged, since only Claude Code's own aliases have been verified. `codex`/`hermes`/
  `opencode` still receive the router's internal catalog id as-is; only `codex`'s `--model`
  flag is documented to accept a bare model name, and none of the three have a verified
  translation table the way `claude_code` now does.
- **`cli/run.py`'s `_candidates()` now sets real `tier`/`capabilities`/`compatible_agents`**
  via `_KNOWN_MODELS`, fixing model auto-detection. Previously every catalog entry got
  `ModelSpec`'s bare defaults (`tier="balanced"`, identical capabilities, no
  `compatible_agents`), so a JEV `"strong"` recommendation could never match any candidate's
  tier and silently fell back to whichever entry the fallback tie-break happened to prefer.
  Worse: with no `"fast"`-tier candidate in the default catalog at all, *every* `"fast"`
  recommendation (the common case — most tasks are simple) fell back to the
  highest-capability candidate, meaning trivial tasks were silently routed to `opus` — the
  opposite of what "fast" means. Fixed by adding `anthropic/claude-fable` (real alias `fable`,
  verified via `claude --help`) and `anthropic/claude-haiku` (real alias `haiku` — not listed
  in `--help`'s examples but confirmed working: `claude --model haiku` passes model validation
  and proceeds to a real API call, unlike a deliberately fake model name, which errors
  immediately with `unrecognized_model`) as genuine fast-tier catalog entries, and assigning
  real tier/capability/compatible-agent metadata to all five default ids. `fable` and `haiku`
  share the same fast-tier capability score and `fable` is listed first, so it wins ties
  deterministically; reorder `models.allow` to prefer `haiku` instead. Live-verified all three
  tiers now resolve distinctly for `claude_code`: trivial → `anthropic/claude-fable`, medium →
  `anthropic/claude-sonnet`, complex → `anthropic/claude-opus`. `compatible_agents` also now
  correctly excludes `openai/coding-strong` from ever winning a `claude_code` launch. Ids not
  in `_KNOWN_MODELS` (e.g. a user's custom catalog addition) still fall back to `ModelSpec`'s
  lenient defaults rather than being rejected.
- README's Roadmap section was removed (it was pre-implementation and out of date); README no
  longer tracks phase-by-phase progress. Trust `src/` and `ARCHITECTURE.md` over README prose
  if either ever disagrees with it.

## Commands

- Python **>= 3.11**, `src/` layout, setuptools build, package name `jev_router`.
- **Zero runtime dependencies (`dependencies = []`) — stdlib only.** Adding a dependency is a
  significant decision; justify it (ARCHITECTURE.md §29: dependency rules). `pytest` is a
  test-only extra (`[project.optional-dependencies] test = ["pytest"]`), not a runtime dep.
- Install: `pip install -e .` (exposes the `jev-router` console script →
  `jev_router.cli.main:main`, which dispatches to `run`/`agents`/`models`/`status`/
  `explain`/`doctor` subcommands). For development, `pip install -e ".[test]"` to get pytest.
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

- **JEV is the only routing authority.** `TYPESAFE_API_KEY` is read exclusively by
  `jev/client.py`; no other module may build JEV auth headers. Never hard-code, commit, or
  print the key. `core/classifier.py` must not grow into an independent LLM router.
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
- Routing is disabled (passthrough) when `TYPESAFE_API_KEY` is absent — the CLI must report
  this clearly instead of crashing a running session.

## Testing rules

- pytest only; `pyproject.toml` `[tool.pytest.ini_options] testpaths = ["tests"]`.
- **Mock the JEV API in all default tests.** Live tests are opt-in: `JEV_LIVE_TESTS=1` plus
  `TYPESAFE_API_KEY` in the environment; never put a real key in fixtures.
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
