# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/), and this project
adheres to [Semantic Versioning](https://semver.org/). There are no tagged releases yet — the
project is at `0.1.0` (see `pyproject.toml`) and everything below is unreleased.

## [Unreleased]

### Changed

- The Jev key is now read from `TYPESAFE_API_KEY`, the name TypeSafe's docs and official SDK
  use, instead of `JEV_API_KEY`. `JEV_API_KEY` is no longer read; if it is set without
  `TYPESAFE_API_KEY`, `jev-claude` / `jev-codex` print a one-line notice to rename it.

### Removed

- The session-start router package `src/jev_router/` (adapters for Claude Code, Codex,
  OpenCode, Hermes and DeepAgents; core router/policy/resolver; contracts; providers;
  transport; state), the `jev-router` command, `configs/` and their tests. The project is now
  the per-turn router `src/jev_router_live/` (`jev-claude`, `jev-codex`, `jev-explain`), which
  never depended on it. Entries below that mention `jev_router`, `jev-router run` or its adapters
  are history.

### Fixed (`jev-claude` live routing)

- JEV was asked twice per turn: Claude Code 2.1.282 resends a turn's first request with
  different injected `<system-reminder>` context, which produced a second conversation key.
- The model catalog was never populated for claude.ai-subscription logins (Claude Code's own
  gateway discovery skips them); the proxy now reads `/v1/models` itself with Claude Code's
  credential and offers JEV the newest model per tier, cheapest first.
- Upstream connection resets mid-stream were silenced as if the client had disconnected; they
  are now logged, and only client-side resets (WinError 10054/10053) stay quiet.
- Responses are streamed as they arrive for every framing (chunked, fixed-length,
  close-delimited), not only chunked.
- Auxiliary calls on the sentinel ran on a static Opus id; they now use their session's routed
  model (or the catalog's Opus).
- 4xx answers from JEV (e.g. a bad key) are no longer retried.
- Interactive Claude Code's next-prompt suggestion request re-routed the conversation after
  every turn (an extra JEV call and a silent model change); it is now treated as auxiliary.
  Local slash-command transcripts (`/model` etc.) are no longer sent to JEV as part of the prompt.
- Security: status files are created owner-only (0600) atomically, the status directory is
  refused if another user owns it, and the status-line `--settings` file is unique and private
  instead of a fixed path in the shared temp dir. `jev-claude` no longer passes
  `--add-dir <package dir>`, which widened Claude Code's file permissions.

### Added

- Safe per-turn decision log line in `~/.jev-claude.log` (no prompt, no credentials).
- `tests/live/test_live_jev_api.py`: opt-in test against the real JEV API.
- `scripts/fake_jev.py`: local System One stand-in for real Claude Code end-to-end runs.

- Core routing pipeline: `core/router.py`, `core/policy.py`, `core/resolver.py`,
  `core/overrides.py`, with turn-scoped state (`state/memory.py`, `state/sqlite.py`).
- Agent adapters for Claude Code, Codex, OpenCode, Hermes, and DeepAgents
  (`adapters/<name>/adapter.py`), each implementing the shared `AgentAdapter` protocol.
- `jev-router` CLI (`run`, `agents`, `models`, `status`, `explain`, `doctor` subcommands).
- `jev-router run --agent <name>` now makes one JEV routing decision at session start and
  launches the real agent binary via `subprocess.run` with that model applied
  (`AgentAdapter.launch_command`).
- Providers for Anthropic, OpenAI, Google, Ollama, OpenRouter, and custom endpoints.
- Transport layer (`transport/http.py`, `sse.py`, `websocket.py`) and observability/security
  modules (structured logging, redaction).
- 58 pytest tests across `tests/unit/`, `tests/integration/`, `tests/adapters/`,
  `tests/contract/`, `tests/routing/`.
- `ARCHITECTURE.md` as the design source of truth, plus `docs/quickstart.md` as the
  integration guide.
- GitHub community files: issue templates, PR template, `CODEOWNERS`,
  `.github/workflows/ci.yml` (runs `python -m pytest` on Python 3.11/3.12), `CODE_OF_CONDUCT.md`,
  `SUPPORT.md`.

### Changed

- `jev/client.py` now calls TypeSafe's real System One API
  (`POST https://api.typesafe.ai/v1/systemone`) with the `{model, state, questions}` request
  shape and `jev-latest` model, instead of a placeholder endpoint.
- The auth environment variable was renamed from `JEV_API_KEY` to `TYPESAFE_API_KEY`, matching
  TypeSafe's own SDK convention.
- `docs/` was collapsed from a 14-file, one-section-per-file mirror of `ARCHITECTURE.md` (plus
  five unused placeholder directories) down to two files: `docs/README.md` and
  `docs/quickstart.md`. `ARCHITECTURE.md` is read directly as the source of truth instead.
- ASCII flow diagrams in `README.md`, `docs/quickstart.md`, and `ARCHITECTURE.md` were
  converted to Mermaid diagrams.
- README's pre-implementation Roadmap section was removed, and CLI usage examples were
  corrected to match the real `jev-router` subcommands.

### Fixed

- `HermesAdapter.detect()` was hardcoded to always return `False`; it now uses
  `shutil.which("hermes")` like every other adapter.
- `launch_command` for `hermes` was missing the required `chat` subcommand
  (`hermes chat --model <m>`); for `opencode`, it now raises `NotImplementedError` instead of
  emitting a `--model` flag that `opencode`'s top-level CLI doesn't actually accept.

## Versioning

This project follows [Semantic Versioning](https://semver.org/):

- **MAJOR**: Incompatible API changes
- **MINOR**: Backward-compatible new functionality
- **PATCH**: Backward-compatible bug fixes
