# Contributing to JEV Model Router

Thank you for your interest in contributing! This document covers how to get set up and how
changes flow into the project.

## Code of Conduct

This project follows our [Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are
expected to uphold this code.

## Development Setup

### 1. Fork and Clone

```bash
git clone https://github.com/<your-username>/jev_model_routers.git
cd jev_model_routers
```

### 2. Install

```bash
pip install -e ".[test]"
```

This requires Python >= 3.11 and pulls in `pytest` (a test-only extra). The project itself has
**zero runtime dependencies** (stdlib only) — adding one is a significant decision that needs
justifying (see `ARCHITECTURE.md` §8, rule 10).

### 3. Set a TypeSafe API Key (optional, for live routing)

Tests mock the JEV API by default, so this isn't required to run the test suite. It is required
to actually exercise routing:

```bash
export TYPESAFE_API_KEY="your_typesafe_api_key"   # PowerShell: $env:TYPESAFE_API_KEY="..."
```

### 4. Run the Tests

```bash
python -m pytest
```

Run a single file or test with:

```bash
python -m pytest tests/unit/test_policy.py
python -m pytest tests/unit/test_policy.py::test_name
```

There is no linter, formatter, or type-checker configured in this repo — don't add one as part
of an unrelated change; verification today is `python -m pytest` plus an import check.

## Making Changes

### Branch Naming

This repo uses conventional prefixes, consistent with its commit history:

| Type | Format | Example |
|------|--------|---------|
| Feature | `feat/<description>` | `feat/cli-run-launches-agent` |
| Bug Fix | `fix/<description>` | `fix/jev-real-endpoint` |
| Documentation | `docs/<description>` | `docs/collapse-docs-split` |
| Maintenance | `chore/<description>` | `chore/remove-skills-lock` |

### Architectural Rules (read before touching `core/`)

The router's dependency direction is one-way: **CLI → adapters → core → contracts**.

- `core/` imports `contracts/` only. Providers and transports are *injected*, never imported.
- Agent-specific protocol knowledge (parsing, proxies, version quirks) lives in
  `adapters/<agent>/` — never `if agent == "claude":` in `core/`.
- Adding a new coding agent should require only a new `adapters/<name>/` directory + fixtures +
  tests + registration in `adapters/registry.py` — **not** a change to `core/router.py`,
  `core/policy.py`, or `core/resolver.py`. This is the project's own definition of success (see
  `ARCHITECTURE.md` §14).

Full rules: `ARCHITECTURE.md` §8 (Architectural Rules) and §7 (Routing Invariants — things that
must not regress, like fail-open behavior and explicit-override-always-wins).

### Coding Standards

- Match the existing terse, low-comment style in `src/jev_router/` — comments explain *why*,
  not *what*.
- No hardcoded values where config already exists (`configs/default.yaml`).
- Never build JEV auth headers outside `jev/client.py`; `TYPESAFE_API_KEY` is read there
  exclusively.
- Never log prompts, keys, or auth headers — `configs/default.yaml` ships
  `privacy.log_prompts: false` by default; keep that semantics.

### Testing

- pytest only (`pyproject.toml` sets `testpaths = ["tests"]`).
- Mock the JEV API in all default tests. Live tests are opt-in via `JEV_LIVE_TESTS=1` plus a
  real `TYPESAFE_API_KEY` — never commit a real key in a fixture.
- Adapter tests are fixture-driven (`tests/fixtures/`): when a protocol changes, capture a
  sanitized upstream request, note the agent version, and assert the expected routing behavior.
- Any non-trivial change to policy, resolution, overrides, fresh-turn detection, state
  isolation, or fallback needs a test — these are the pure-logic hot spots.

### Commit Guidelines

Use [Conventional Commits](https://www.conventionalcommits.org/) style, matching this repo's
history: `feat: ...`, `fix: ...`, `docs: ...`, `chore: ...`, `test: ...`. Keep the subject line
imperative and under ~72 characters.

## Pull Request Process

1. Push your branch and open a PR — the PR template will guide you through the checklist.
2. Make sure `python -m pytest` passes; CI (`.github/workflows/ci.yml`) runs it on Python 3.11
   and 3.12.
3. If the change alters routing behavior, update `ARCHITECTURE.md` alongside the code (not
   `docs/*` — see the note at the top of `docs/README.md`).

## Reporting Issues

Use the issue templates (Bug Report, Feature Request, Documentation) when opening an issue.

### Security Issues

For security issues, see [SECURITY.md](SECURITY.md). **Do not** open a public issue for a
security vulnerability.

## License

By contributing, you agree that your contributions will be licensed under the project's
[MIT license](LICENSE).

## Questions?

Open a [discussion](https://github.com/himanshu231204/jev_model_routers/discussions) or an
issue with the `question` label.

Thank you for contributing to JEV Model Router!
