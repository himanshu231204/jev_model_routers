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
justifying.

### 3. Set a Jev key (optional, for live routing)

Tests mock Jev by default, so this isn't required to run the test suite. It is required to
actually exercise routing (a TypeSafe key; `TYPESAFE_API_KEY` is the only variable read):

```bash
export TYPESAFE_API_KEY="your_typesafe_key"   # PowerShell: $env:TYPESAFE_API_KEY="..."
```

### 4. Run the Tests

```bash
python -m pytest
```

Run a single file or test with:

```bash
python -m pytest tests/live/test_live_policy.py
python -m pytest tests/live/test_live_policy.py::test_name
```

Against the real Jev API (opt-in): `JEV_LIVE_TESTS=1 python -m pytest tests/live/test_live_jev_api.py -s`.
For a real Claude Code run without Jev access, see `scripts/fake_jev.py`.

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

### Architectural Rules (read before touching `src/jev_router_live/`)

- Keep the module boundaries: the Jev client (`stdlib_router.py`) knows nothing about Claude
  Code; `policy.py` is pure (no I/O); `proxy.py` is the only module that understands the
  Anthropic wire format. Don't add a second router, Jev client or proxy.
- Claude Code must keep working exactly as usual: rewrite only the model (and fields that model
  cannot accept), stream responses through, and fall back rather than block on any failure.

Full rules: `AGENTS.md` (routing invariants — things that must not regress, like one Jev call
per turn, explicit-choice-always-wins and fail-open) and `ARCHITECTURE.md`.

### Coding Standards

- Match the existing terse, low-comment style — comments explain *why*, not *what*.
- Routing thresholds and model ids belong in `config.py`, not scattered through the code.
- `TYPESAFE_API_KEY` is read only by the Jev client; never log prompts, keys or auth headers. The
  decision log (`log.record`) takes safe metadata only.

### Testing

- pytest only (`pyproject.toml` sets `testpaths = ["tests"]`); tests live in `tests/live/`.
- Mock Jev in all default tests. The real-API test is opt-in via `JEV_LIVE_TESTS=1` plus a real
  `TYPESAFE_API_KEY` — never commit a real key in a fixture.
- Proxy tests run against a local fake Anthropic upstream; when Claude Code's request shapes
  change, model the test on captured real traffic and note the Claude Code version.
- Any non-trivial change to policy, turn detection, pinning, catalog, rewriting, streaming,
  fallback or file handling needs a test.

### Commit Guidelines

Use [Conventional Commits](https://www.conventionalcommits.org/) style, matching this repo's
history: `feat: ...`, `fix: ...`, `docs: ...`, `chore: ...`, `test: ...`. Keep the subject line
imperative and under ~72 characters.

## Pull Request Process

1. Push your branch and open a PR — the PR template will guide you through the checklist.
2. Make sure `python -m pytest` passes; CI (`.github/workflows/ci.yml`) runs it on Python 3.11
   and 3.12.
3. If the change alters routing behavior, update `ARCHITECTURE.md` alongside the code, and
   `README.md` / `docs/quickstart.md` if users will notice.

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
