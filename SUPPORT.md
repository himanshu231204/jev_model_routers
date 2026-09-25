# Support

Thank you for using JEV Model Router! This document explains how to get help.

## Getting Help

### Documentation

- **README**: [README.md](README.md) — installation, quick start, screenshots
- **Quickstart guide**: [docs/quickstart.md](docs/quickstart.md) — using `jev-claude`, reading decisions, troubleshooting
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
3. Check `~/.jev-claude.log` — every routing decision and failure is logged there (re-run with
   `JEV_DEBUG=1` for request-level detail), and the quickstart's Troubleshooting table covers
   the common cases
4. Reproduce the issue — ensure you can reproduce it consistently

### How to Report

1. Create an issue using the Bug Report template
2. Include:
   - Clear description
   - Steps to reproduce (including the exact `jev-claude` / `jev-codex` command used)
   - Expected vs actual behavior
   - Environment details (OS, Python version, `claude --version`)
   - The relevant `~/.jev-claude.log` lines (they contain no prompts or keys; remove any
     `JEV_DEBUG` prompt excerpts before posting)

### After Reporting

- We will acknowledge your report and ask for clarification if needed

## Requesting Features

### Before Requesting

1. Check existing issues — your feature may already be requested
2. Check `ARCHITECTURE.md` — including its Known Limitations section

### How to Request

1. Create an issue using the Feature Request template
2. Include a clear description, your use case, and alternatives considered

## Frequently Asked Questions

**Q: What is JEV Model Router?**
A: A local proxy for Claude Code (and OpenAI Codex) that picks the cheapest capable Claude
model for each new turn, using TypeSafe's Jev decision model, while Claude Code works as usual.

**Q: Is it free?**
A: Yes, it's open source under the MIT license. You do need your own
[TypeSafe](https://typesafe.ai/) API key to enable routing.

**Q: How do I get started?**
A: See the Quick Start section in [README.md](README.md#quick-start).

**Q: How can I contribute?**
A: See [CONTRIBUTING.md](CONTRIBUTING.md).

**Q: Claude Code prints `[claude-code:unrecognized_model] {"model":"jev-router"}` at startup — is that a bug?**
A: No — it's a harmless one-line warning from Claude Code about the "JEV Router" entry; requests
are still routed. See the quickstart's Troubleshooting table.

**Q: Does it replace Claude?**
A: No. Jev only decides which Claude model handles each turn; Claude still does the work.

## Community Guidelines

- Be respectful — treat everyone with respect
- Be helpful — answer questions when you can
- Be patient — allow time for responses

## Security

For security issues, see [SECURITY.md](SECURITY.md). Do not create public issues for security
vulnerabilities.

---

Thank you for being part of the JEV Model Router community!
