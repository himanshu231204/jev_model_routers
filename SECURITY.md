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
- Affected file(s)/component(s) — e.g. `jev/client.py`, `security/secrets.py`, a specific
  adapter
- Suggested fix, if you have one

### What to Expect

1. Acknowledgment of your report
2. Confirmation of the vulnerability and an assessment of its impact
3. A fix, released once verified
4. Public disclosure after the fix ships (with credit, if you want it)

## Scope and Known Sensitive Areas

This router handles a `TYPESAFE_API_KEY` and, depending on configuration, prompt content and
repository context sent to TypeSafe's Jev API. The invariants below are the ones most worth
checking when reviewing for security issues (see `ARCHITECTURE.md` §7 for the full list):

- **`TYPESAFE_API_KEY` is read exclusively by `jev/client.py`.** No other module should build
  JEV auth headers, and the key must never be hard-coded, committed, printed, or logged.
  `security/secrets.py` enforces this at the code level — it raises if anything else tries to
  read that key directly.
- **Prompts, keys, and auth headers are never logged by default.** `configs/default.yaml` ships
  `privacy.log_prompts: false` and `privacy.send_repository_content: false`.
- **Fail-open, not fail-silent.** Missing key, timeout, or malformed JEV response falls back to
  the current/default model rather than blocking — but the fallback reason is always recorded,
  never swallowed.

If you find a gap in any of the above — a code path that logs a prompt, a place that could leak
the API key, or a way to bypass the fail-open fallback silently — that's exactly the kind of
report this policy is for.

## Security Best Practices for Users

- Store `TYPESAFE_API_KEY` in an environment variable or secret manager — never in a config
  file committed to version control.
- Keep `privacy.log_prompts` and `privacy.send_repository_content` at their default `false`
  unless you specifically need otherwise.
- This project has zero runtime dependencies (stdlib only), which keeps the supply-chain
  surface minimal — if a PR proposes adding one, that's worth extra scrutiny (see
  `ARCHITECTURE.md` §8, rule 10).

---

Thank you for helping keep JEV Model Router and its users safe.
