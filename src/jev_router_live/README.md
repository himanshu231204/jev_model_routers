# jev_router_live

Per-turn live model routing for Claude Code and OpenAI Codex.

`jev_router` (the rest of this repository) makes one routing decision at session start. This
package takes a different approach: a local HTTP proxy sits in front of the agent CLI's own
API and rewrites **every fresh user turn** to the cheapest model tier that can do the work,
via TypeSafe's Jev (System One) API — while the agent's own picker, tools, permissions, and
session handling are untouched.

## Install

```bash
pip install -e .
echo "JEV_API_KEY=..." > ~/.jev-router.env
```

## Use

```bash
jev-claude                # launches Claude Code with per-turn routing
jev-codex                 # launches OpenAI Codex with per-turn routing
jev-explain <session-id>  # shows why the last turn was routed the way it was
```

Both commands launch the real upstream CLI (`claude` / `codex` must already be installed and
logged in) and only choose the model for each fresh turn. Set `JEV_NO_STATUSLINE=1` to skip
installing the bundled Claude Code status line, or `JEV_DEBUG=1` to log routing decisions to
`~/.jev-claude.log`.

## Known behavior (Claude Code)

- **`[claude-code:unrecognized_model] {"model":"jev-router"}` on startup is harmless.**
  Claude Code 2.1.281 validates the model name client-side before the first request; the
  sentinel `jev-router` is not in its catalog, so it prints this one-line warning (telemetry
  only — the emitter returns void, is try/caught, and is deduped per model id). The request
  still reaches the proxy and is rewritten to a real model; verified end-to-end: Claude
  completes responses with the warning present. The sentinel mechanism is intentional and
  must not be removed.
- **Model catalog is best-effort.** The proxy records exact model ids from any `GET /v1/models`
  Claude Code makes through it and prefers them. Claude Code 2.1.281 has not been observed
  issuing that call in `-p` (print) runs, even with `CLAUDE_CODE_ENABLE_GATEWAY_MODEL_DISCOVERY=1`
  and a healthy upstream, so routing typically uses the static tier ids — which are verified
  against Claude Code's own shipped model catalog (see `config.py` `TIERS`), never assumed.

## Layout

| Module | Responsibility |
| --- | --- |
| `config.py` | Tiers, thresholds, override phrases, Jev questions |
| `policy.py` | Pure routing decision function |
| `router.py` | Jev/System One HTTP call (stdlib `urllib`, no SDK) |
| `proxy.py` | Claude Code per-turn proxy |
| `codex_proxy.py` | Codex per-turn proxy |
| `status.py` | Per-session decision file, used by the status line and `jev-explain` |
| `explain.py` | Renders the explanation report |
| `settings.py` | Restores Claude Code's saved default model on exit |
| `env_file.py` | Minimal `.env` loader shared by both launchers |
| `bin/jev_claude.py`, `bin/jev_codex.py`, `bin/jev_statusline.py`, `bin/jev_explain.py` | the four CLI entry points |

`skills/codex/jev-explain/SKILL.md` is the `$jev-explain` skill for Codex, installed
automatically into `~/.agents/skills/jev-router-explain/SKILL.md` by `jev-codex` on launch
(see `install_codex_skill` in `bin/jev_codex.py`). It invokes `jev-explain` directly.

The Claude Code equivalent (`/jev-explain`, a `.claude/skills/jev-explain/SKILL.md` that
shells out to `python3 -m jev_router_live.bin.jev_explain "$CLAUDE_SESSION_ID"`) is not
checked into this repository because `.claude/` is gitignored here; copy it into your own
project's `.claude/skills/` if you want the slash command.

See `ARCHITECTURE.md` §16 for the full design of this package, including how it fits
alongside `jev_router`'s session-start routing.
