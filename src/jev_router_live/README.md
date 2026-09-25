# jev_router_live

Per-turn live model routing for Claude Code and OpenAI Codex.

A local HTTP proxy sits in front of the agent CLI's own API and rewrites **every fresh user
turn** to the cheapest model tier that can do the work, via TypeSafe's Jev (System One) API —
while the agent's own picker, tools, permissions, and session handling are untouched.

## Install

```bash
pip install -e .
echo "TYPESAFE_API_KEY=..." > ~/.jev-router.env
```

## Use

```bash
jev-claude                # launches Claude Code with per-turn routing
jev-codex                 # launches OpenAI Codex with per-turn routing
jev-explain <session-id>  # shows why the last turn was routed the way it was
```

Both commands launch the real upstream CLI (`claude` / `codex` must already be installed and
logged in) and only choose the model for each fresh turn. `TYPESAFE_API_KEY` is the only credential
read; without it `jev-claude` starts plain Claude Code with no proxy.

In Claude Code, `/model` shows an extra **JEV Router** row, selected by default for the
session (it is never saved as your default). Pick a real model to turn routing off; pick
JEV Router again to turn it back on.

| Variable | Effect |
| --- | --- |
| `TYPESAFE_API_KEY` | TypeSafe key for Jev. Required for routing. |
| `JEV_ALLOW_FABLE=1` | Also offer Fable (bills extra usage credits). |
| `JEV_NO_STATUSLINE=1` | Don't install the routing status line (yours is never overridden anyway). |
| `JEV_DEBUG=1` | Add request-level tracing, including the first 60 characters of each routed prompt. |
| `JEV_ENDPOINT` | Override the System One URL (testing). |
| `JEV_CLIENT=sdk` | Use the optional TypeSafe SDK instead of stdlib HTTP (`pip install "jev-model-router[typesafe]"`). |

## Debugging

- `~/.jev-claude.log` always gets one safe line per routed turn
  (`turn=… decision=sonnet model=claude-sonnet-5 confidence=0.99 latency=412ms reason=jev`),
  the model catalog the proxy read, and every routing, catalog or upstream failure. Prompts,
  keys and headers are never written there.
- `jev-explain <session-id>` (or `/jev-explain`) shows the full last decision: prompt, Jev's
  scores, recommendation and the policy reason. That data lives in an owner-only file under
  `<tempdir>/jev-claude/` and is deleted after 7 days idle.
- `reason=` values: `jev` (followed Jev), `override` (prompt said e.g. "use opus"),
  `jev-unavailable` (Jev failed; kept current), `low-confidence-*`,
  `downgrade-not-worth-cache-rebuild`, `…+unavailable` (nearest available tier), `…/no-change`.

## Tests

```bash
python -m pytest -q                                   # everything, Jev mocked
JEV_LIVE_TESTS=1 TYPESAFE_API_KEY=... \
  python -m pytest tests/live/test_live_jev_api.py -s # real Jev: trivial/medium/hard
```

For a real Claude Code run without network access to Jev, `scripts/fake_jev.py` is a local
System One stand-in: `python scripts/fake_jev.py 8765`, then
`JEV_ENDPOINT=http://127.0.0.1:8765/v1/systemone TYPESAFE_API_KEY=local jev-claude -p "…"`.

## Known behavior (Claude Code)

- **`[claude-code:unrecognized_model] {"model":"jev-router"}` on startup is harmless.**
  Claude Code 2.1.281+ validates the model name client-side before the first request; the
  sentinel `jev-router` is not in its catalog, so it prints this one-line warning (telemetry
  only — the emitter returns void, is try/caught, and is deduped per model id). The request
  still reaches the proxy and is rewritten to a real model; verified end-to-end: Claude
  completes responses with the warning present. The sentinel mechanism is intentional and
  must not be removed.
- **The proxy reads the model catalog itself.** Claude Code's gateway model discovery only
  runs with an API key / `ANTHROPIC_AUTH_TOKEN` / `apiKeyHelper`, so with a claude.ai
  subscription login it never calls `/v1/models`. On the first routed turn the proxy calls
  `/v1/models` once with that request's own credential (2 s timeout) and offers Jev the newest
  model per tier. If that fails, it uses the static ids in `config.py` `TIERS`, verified
  against Claude Code's shipped model catalog — never invented ones.
- **Claude Code resends a turn's first request.** 2.1.282 sends it twice with different
  injected context; the proxy recognises the same turn and asks Jev once.

## Known limitations

- The interactive `/model` row is created by Claude Code from `ANTHROPIC_CUSTOM_MODEL_OPTION*`
  (confirmed in 2.1.282's source); it depends on those variables staying supported.
- The first routed turn of a process can take up to ~5 s longer in the worst case (2 s catalog
  read + 3 s Jev deadline) when both are slow; normal cost is one Jev call (~0.3-1 s).
- Routing is per turn, not per tool call: a turn that turns out harder than its prompt looked
  stays on its model until the next user turn.

## Layout

| Module | Responsibility |
| --- | --- |
| `config.py` | Tiers, thresholds, override phrases, Jev questions |
| `policy.py` | Pure routing decision function |
| `router.py` | `ask_jev` dispatcher: stdlib client by default, SDK with `JEV_CLIENT=sdk` |
| `stdlib_router.py` | The Jev/System One client (stdlib `urllib`): request, timeouts, retries, parsing |
| `sdk_router.py` | Optional client via the TypeSafe SDK |
| `proxy.py` | Claude Code per-turn proxy |
| `codex_proxy.py` | Codex per-turn proxy |
| `status.py` | Per-session decision file, used by the status line and `jev-explain` |
| `explain.py` | Renders the explanation report |
| `settings.py` | Restores Claude Code's saved default model on exit |
| `env_file.py` | Minimal `.env` loader shared by both launchers |
| `bin/jev_claude.py`, `bin/jev_codex.py`, `bin/jev_statusline.py`, `bin/jev_explain.py` | the four CLI entry points |

`skills/codex/jev-explain/SKILL.md` (inside this package, shipped as package data so it exists
in every install) is the `$jev-explain` skill for Codex, installed automatically into
`~/.agents/skills/jev-router-explain/SKILL.md` by `jev-codex` on launch (see
`install_codex_skill` in `bin/jev_codex.py`). It invokes `jev-explain` directly.

The Claude Code equivalent (`/jev-explain`, a `.claude/skills/jev-explain/SKILL.md` that
shells out to `python3 -m jev_router_live.bin.jev_explain "$CLAUDE_SESSION_ID"`) is not
checked into this repository because `.claude/` is gitignored here; copy it into your own
project's `.claude/skills/` if you want the slash command.

See `ARCHITECTURE.md` at the repository root for the full design.
