# Security Policy

## Supported Versions

This project is pre-1.0 (currently `0.1.0`) and has no tagged releases yet. Security fixes are
made against the `main` branch — there is no older version being maintained in parallel.

| Version | Supported |
|---------|-----------|
| `main` / `0.1.0` | Yes |

## Reporting a Vulnerability

**Do not report security vulnerabilities through public GitHub issues.**

Preferred: use GitHub's private vulnerability reporting for this repository —
[github.com/himanshu231204/jev_model_routers/security/advisories/new](https://github.com/himanshu231204/jev_model_routers/security/advisories/new).
If that's unavailable, reach the maintainer directly via their GitHub profile
([@himanshu231204](https://github.com/himanshu231204)).

### What to Include

- Description of the vulnerability and its potential impact
- Steps to reproduce
- Affected file(s)/component(s) — e.g. `src/jev_router_live/proxy.py`, `stdlib_router.py`,
  `status.py`
- Suggested fix, if you have one

### What to Expect

1. Acknowledgment of your report
2. Confirmation of the vulnerability and an assessment of its impact
3. A fix, released once verified
4. Public disclosure after the fix ships (with credit, if you want it)

## Scope and Known Sensitive Areas

The router runs a local proxy in front of Claude Code's API traffic, handles a `TYPESAFE_API_KEY`,
and sends each new turn's prompt to TypeSafe's Jev API. The invariants below are the ones most
worth checking when reviewing for security issues (see `ARCHITECTURE.md` §12 for detail):

- **`TYPESAFE_API_KEY` is the only Jev credential**, read in one place (`config.py`). It must
  never be hard-coded, committed, printed or logged. The earlier name `JEV_API_KEY` is not read.
- **Claude Code's own credentials pass through untouched.** The proxy binds to `127.0.0.1` and
  reuses Claude Code's credential only to read `/v1/models` from the same upstream.
- **Prompts, keys and auth headers are never logged.** The decision log holds safe metadata
  only; prompts appear only in the owner-only status file (and with opt-in `JEV_DEBUG`).
- **Local files are private.** The status directory is used only if it is owned by the current
  user with mode 0700 (a directory pre-created by another user on shared `/tmp` is refused);
  files are created 0600; the status-line settings file has a unique name and is deleted on exit.
- **Fail-open, not fail-silent.** Missing key, timeout or malformed Jev response falls back to a
  safe model rather than blocking — but the reason is always logged, never swallowed.
- **Claude Code's permissions are not widened** (no extra `--add-dir`, no settings beyond the
  status line).

If you find a gap in any of the above — a code path that logs a prompt, a place that could leak
a key, a way to make another local user's data or settings load, or a way to bypass the
fail-open fallback silently — that's exactly the kind of report this policy is for.

## Security Best Practices for Users

- Store `TYPESAFE_API_KEY` in an environment variable, `~/.jev-router.env` (readable only by you) or a
  secret manager — never in a file committed to version control.
- Leave `JEV_DEBUG` off in normal use; it writes prompt excerpts to `~/.jev-claude.log`.
- This project has zero runtime dependencies (stdlib only), which keeps the supply-chain surface
  minimal — if a PR proposes adding one, that's worth extra scrutiny.

---

Thank you for helping keep JEV Model Router and its users safe.
