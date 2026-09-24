# Support

Thank you for using JEV Model Router! This document explains how to get help.

## Getting Help

### Documentation

- **README**: [README.md](README.md) — installation, quick start, CLI reference
- **Quickstart guide**: [docs/quickstart.md](docs/quickstart.md) — full integration guide
- **Architecture**: [ARCHITECTURE.md](ARCHITECTURE.md) — design, invariants, rules
- **Changelog**: [CHANGELOG.md](CHANGELOG.md) — version history

### Community

- **GitHub Discussions**: [Discussions](https://github.com/himanshu231204/jev_model_routers/discussions) — ask questions, share ideas

### Direct Support

- **Issues**: [GitHub Issues](https://github.com/himanshu231204/jev_model_routers/issues) — bug reports and feature requests

## Reporting Bugs

### Before Reporting

1. Search existing issues — your bug may already be reported
2. Check the README and `docs/quickstart.md` — the answer may already be documented
3. Run `jev-router doctor` — it diagnoses common environment/config issues
4. Reproduce the issue — ensure you can reproduce it consistently

### How to Report

1. Create an issue using the Bug Report template
2. Include:
   - Clear description
   - Steps to reproduce (including the exact `jev-router` command used)
   - Expected vs actual behavior
   - Environment details (OS, Python version, `jev-router --help` output)

### After Reporting

- We will acknowledge your report and ask for clarification if needed

## Requesting Features

### Before Requesting

1. Check existing issues — your feature may already be requested
2. Check `ARCHITECTURE.md` — it may already be planned (see §12 Implementation Phases)

### How to Request

1. Create an issue using the Feature Request template
2. Include a clear description, your use case, and alternatives considered

## Frequently Asked Questions

**Q: What is JEV Model Router?**
A: An agent-agnostic model-routing layer that sits between coding agents (Claude Code, Codex,
OpenCode, DeepAgents, Hermes) and the models they use, picking the right model per session via
TypeSafe's Jev decision model.

**Q: Is it free?**
A: Yes, it's open source under the MIT license. You do need your own
[TypeSafe](https://typesafe.ai/) API key to enable routing.

**Q: How do I get started?**
A: See the Quick Start section in [README.md](README.md#quick-start).

**Q: How can I contribute?**
A: See [CONTRIBUTING.md](CONTRIBUTING.md).

**Q: `jev-router run --agent opencode` (or `deepagents`) fails immediately — is that a bug?**
A: No — expected. Neither has a working subprocess launch path yet; see
[docs/quickstart.md](docs/quickstart.md#1-cli-wrapper) for why.

## Community Guidelines

- Be respectful — treat everyone with respect
- Be helpful — answer questions when you can
- Be patient — allow time for responses

## Security

For security issues, see [SECURITY.md](SECURITY.md). Do not create public issues for security
vulnerabilities.

---

Thank you for being part of the JEV Model Router community!
