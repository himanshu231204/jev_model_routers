# SDK Optional-Extra Design — `typesafe-sdk` behind a stdlib-default interface

Date: 2026-09-25
Status: spec (conversational design approved §1–§5; awaiting file review)
Path: architectural (announced upfront; no downgrade)

## Intent (agreed brief)

- Outcome: `typesafe-sdk` as **optional extra**; stdlib `urllib` stays the default. Zero-deps promise preserved.
- Scope: both `src/jev_router/jev/` (session-start router) and `src/jev_router_live/` (per-turn proxy).
- Constraint: **best-effort** parity — never blocks a prompt; SDK retry/timeout may follow SDK defaults instead of exact 1500/3000ms wall-clock.
- Invariants kept: `JEVDecision` stays the boundary; `core/` never imports SDK; `TYPESAFE_API_KEY` remains sole secret; fail-open with recorded reason; no prompts/keys/raw bodies in logs by default.

## Current state (from `src/` + live docs)

- `jev/client.py`: stdlib `urllib` POST `{JEV_ENDPOINT|https://api.typesafe.ai/v1/systemone}`, Bearer `TYPESAFE_API_KEY`. Daemon-thread + `join(remaining)` wall-clock deadline (`timeout_ms=1500`, `deadline_ms=3000`, `max_retries=1`). Returns `(JEVDecision|None, ms, reason)` with `missing_api_key/deadline_exceeded/jev_error:X`.
- `jev/questions.py`: `{model: jev-latest, state: {...}, questions: {tier: {type: choice, instructions, criteria: {fast,balanced,strong}}}}`.
- `jev/normalize.py` → `JEVDecision` from `{answers.tier.choice, confidence}`.
- `jev_router_live/router.py`: same urllib+wall-clock pattern but different shape: `state: {request, session, environment}`, `questions: {task_complexity/reasoning_required/tool_complexity: {type: score, prompt, scale}, model: {type: choice, prompt: [...], options: {...}}}`. `prompt/scale/options` vs SDK `instructions/criteria` mismatch flagged.
- `pyproject.toml`: `dependencies = []`. `ARCHITECTURE.md` is 16 sections; the `§29 dependency rules` ref in `AGENTS.md` is stale.
- SDK (fetched live): `pip install typesafe-sdk`, `TypeSafeClient/AsyncTypeSafeClient.system_one(state, {name: Choice/Noul/Score})` → `result.choices[].choice/confidence/probabilities`; env `TYPESAFE_API_KEY/BASE_URL/DEFAULT_MODEL/LOG_LEVEL`; `RetryPolicy`; bodies NOT redacted at `debug`; invalid key raises at construction.

## Decision

Approach 1: interface + lazy optional extra. (Rejected: tooling-only SDK, full replacement.)

## §1 Architecture

`core/` stays pure. Seam only inside the two `jev/` transport boundaries:
- `src/jev_router/jev/base.py`: `Protocol ask(payload)` + `CLIENT_KINDS` + pure `resolve_client_kind(config)`.
- Existing `JevClient` stays as `StdlibJevClient` (same behavior); new `SdkJevClient` implements same protocol via lazy import; missing extra → `missing_extra` reason (fail-open).
- `live/`: `router.py` split into `stdlib_router.py` (moved as-is) + `sdk_router.py`, same `dict|None` return into `policy.decide()`.
- Selection via config precedence: new `jev.client: stdlib|sdk` + `JEV_CLIENT` env, default `stdlib`. Factories in `jev/__init__.py` / `live/__init__.py` only place that touches SDK path, only when selected.
- `pyproject.toml`: `dependencies=[]` unchanged; add `[project.optional-dependencies] typesafe=["typesafe-sdk"]`.
- No changes to `contracts/`, `core/policy.py`, `core/resolver.py`, `state/`, `adapters/`.

## §2 Components

- `jev/base.py` (~30 lines): protocol + kinds + resolver, no impl imports.
- `jev/sdk_client.py` (~80 lines): same ctor signature `(timeout_ms, deadline_ms, max_retries)`; lazy `Choice, TypeSafeClient, RetryPolicy`; `questions.tier` → `Choice(instructions, criteria)`; `state` passthrough; `model` → client param; `RetryPolicy(max_retries, timeout=timeout_s)` + outer daemon-thread `join(deadline_s)` for best-effort cap.
- `live/sdk_router.py` (~70 lines): same wrapper; score questions passed as raw dicts + OpenAPI verification task; API rejection → `None` fail-open, stdlib unaffected.
- Factories (~15 lines each): default stdlib; SDK only on explicit opt-in; ImportError → stdlib + `missing_extra`.
- Config: `configs/default.yaml` `jev.client: stdlib`; `config/schema.py` + `loader.py` accept/validate; `ARCHITECTURE.md` §10 update + fix stale §29 ref.

## §3 Data flow

`NormalizedRequest → build_jev_payload() → {model, state, questions.tier} → Stdlib.ask() | Sdk.ask() → normalize (accepts raw dict OR SDK result object, duck-typed .choices) → identical JEVDecision → Policy.evaluate() untouched → resolver → pin.`
Live mirrors: `new_turn_prompt → ask_jev() → stdlib_router | sdk_router → same {choice, confidence, probabilities, metrics, request, response, ms}|None → policy.decide() untouched.`
Env: `JEV_ENDPOINT` wins, else `TYPESAFE_BASE_URL`, else default. Key passed explicitly as `api_key=`; sole-reader invariant holds by pass-through.

## §4 Error handling

All SDK exceptions translated, never raised past `ask()`:
- `ImportError` → `(None, ms, missing_extra)` + one-line hint.
- Construction `TypeSafeError` → `(None, 0, missing_api_key)` (same string as stdlib).
- `TypeSafeAPIError/APIConnectionError/APITimeoutError` → `(None, ms, jev_error:<ClassName>)`.
- Absent/unknown `tier` → `(None, ms, malformed_jev_response)`.
- Outer `join(deadline_s)` caps total wait → `(None, deadline_ms, deadline_exceeded)`.
- Privacy: wrapper forces SDK logger to `WARNING` unless `jev.allow_debug_logs: true`; never forwards `raw_http_response` to logs; live 0600 session file unchanged.

## §5 Testing

- `tests/unit/test_sdk_parity.py` (mocked SDK): strong@0.97 → accepted; 0.27 → low-confidence keep; missing key/timeout/malformed → same reasons as stdlib.
- Factory tests: default stdlib; `JEV_CLIENT=sdk` w/o extra → stdlib + `missing_extra`; with mocked SDK → SDK; `JEV_ENDPOINT` > `TYPESAFE_BASE_URL` > default.
- `tests/live/test_sdk_router.py`: mocked `system_one` → same shape; `prompt/scale` rejection → `None`.
- No-live-key rule kept (`JEV_LIVE_TESTS=1` opt-in only).
- Done = pytest green, no diff outside `jev/`, `live/`, `config/`, `ARCHITECTURE.md`, privacy logger-level test.

## Open verification before implementation

- Confirm live `prompt/scale/options` against OpenAPI `https://api.typesafe.ai/docs/`; if rejected, SDK live path ships as choice-only or stays fail-open.
- Confirm `typesafe-sdk` transitive deps for the optional-extra pin.

## Spec self-review

- Placeholders: none — file paths, reason strings, config keys concrete.
- Consistency: best-effort deadline (§4) matches brief; both-paths scope reflected in §1/§2/§5; zero-dep default preserved throughout.
- Scope: single plan (interface + two SDK shims + config + parity tests). No async, no response_model generics.
- Ambiguity: `model` value `jev-latest` vs SDK `model="jev"` — implementation to pass stored payload `model` through verbatim; `TYPESAFE_DEFAULT_MODEL` not relied upon.
