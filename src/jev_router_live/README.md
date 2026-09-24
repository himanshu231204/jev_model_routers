# jev_router_live

A Python port of [gargpratyush/jev-router](https://github.com/gargpratyush/jev-router).

`jev_router` (the rest of this repository) makes one routing decision at session start.
This package is a different design: a local HTTP proxy sits in front of the agent CLI's own
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
jev-claude              # launches Claude Code with per-turn routing
jev-codex                # launches OpenAI Codex with per-turn routing
jev-explain <session-id>  # shows why the last turn was routed the way it was
```

Both commands launch the real upstream CLI (`claude` / `codex` must already be installed and
logged in) and only choose the model for each fresh turn. Set `JEV_NO_STATUSLINE=1` to skip
installing the bundled Claude Code status line, or `JEV_DEBUG=1` to log routing decisions to
`~/.jev-claude.log`.

## Layout

| Module | Port of |
| --- | --- |
| `config.py` | `src/config.mjs` — tiers, thresholds, override phrases, Jev questions |
| `policy.py` | `src/policy.mjs` — pure decision function |
| `router.py` | `src/router.mjs` — Jev/System One HTTP call (stdlib `urllib`, no SDK) |
| `proxy.py` | `src/proxy.mjs` — Claude Code per-turn proxy |
| `codex_proxy.py` | `src/codex-proxy.mjs` — Codex per-turn proxy |
| `status.py` | `src/status.mjs` — per-session decision file, used by the status line and `jev-explain` |
| `explain.py` | `src/explain.mjs` — renders the explanation report |
| `settings.py` | `src/settings.mjs` — restores Claude Code's saved default model on exit |
| `bin/jev_claude.py`, `bin/jev_codex.py`, `bin/jev_statusline.py`, `bin/jev_explain.py` | the four `bin/*.mjs` launchers |

`skills/codex/jev-explain/SKILL.md` is the `$jev-explain` skill file for Codex, installed
automatically into `~/.agents/skills/jev-router-explain/SKILL.md` by `jev-codex` on launch
(see `install_codex_skill` in `bin/jev_codex.py`). It invokes `jev-explain` directly.

The Claude Code equivalent (`/jev-explain`, a `.claude/skills/jev-explain/SKILL.md` that
shells out to `python3 -m jev_router_live.bin.jev_explain "$CLAUDE_SESSION_ID"`) is not
checked into this repository because `.claude/` is gitignored here; copy it into your own
project's `.claude/skills/` if you want the slash command.
