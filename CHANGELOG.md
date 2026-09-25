# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/), and this project
adheres to [Semantic Versioning](https://semver.org/). Releases are published to PyPI as
[`jev-model-router`](https://pypi.org/project/jev-model-router/) when a `v*` tag is pushed — see
[`RELEASE.md`](RELEASE.md).

## [Unreleased]

### Added
- Docker image (`Dockerfile`, published to `ghcr.io/himanshu231204/jev_model_routers` on
  each tagged release) bundling `jev-claude`/`jev-codex` with the CLIs they wrap.

## [0.1.0] - 2026-09-25

First public release: per-turn model routing for Claude Code, decided by TypeSafe's Jev.

### Added

- **`jev-claude`** — runs the real Claude Code CLI behind a local proxy and adds a
  **JEV Router** entry to `/model`. Each new user turn asks Jev once which of your account's
  models (newest Haiku / Sonnet / Opus) fits it; the turn's whole tool loop stays on that model.
  Picking a model in `/model` turns routing off; picking JEV Router turns it back on.
- **Policy layer** — explicit choices ("use opus" in the prompt, or `/model`) always win; low
  confidence never downgrades; long conversations aren't downgraded (prompt-cache rebuild); only
  models the account actually has are used, read from its own `/v1/models` catalog.
- **Fail-open** — no key, a Jev timeout (3 s deadline), an error or a malformed answer never
  blocks a turn: Claude Code continues on a safe model and the reason is logged.
- **Streaming preserved** — responses are relayed as they arrive; only the request's model (and
  fields that model can't accept) is changed.
- **Explainability** — a status line showing each turn's model and confidence, `jev-explain`
  for the full reasoning, and one safe line per decision in `~/.jev-claude.log`.
- **`jev-codex`** *(experimental)* — the same routing for the OpenAI Codex CLI, with a
  `$jev-explain` skill.
- **Privacy and security** — the TypeSafe key (`TYPESAFE_API_KEY`) and prompts are never logged;
  local status files are owner-only and refused in directories owned by other users; Claude
  Code's permissions are not widened.
- Optional `typesafe` extra to call Jev through the official `typesafe-sdk` (`JEV_CLIENT=sdk`).
- Zero runtime dependencies; Python 3.11+.

[Unreleased]: https://github.com/himanshu231204/jev_model_routers/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/himanshu231204/jev_model_routers/releases/tag/v0.1.0
