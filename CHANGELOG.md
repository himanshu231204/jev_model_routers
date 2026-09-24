# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/), and this project
adheres to [Semantic Versioning](https://semver.org/). There are no tagged releases yet — the
project is at `0.1.0` (see `pyproject.toml`) and everything below is unreleased.

## [Unreleased]

### Added

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
