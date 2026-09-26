# Quick Start — Using JEV Router with Claude Code

> Set up `jev-claude`, use it day to day, and understand what it decided.

---

## 1. Prerequisites

- **Python ≥ 3.11**
- **[Claude Code](https://code.claude.com/docs/en/setup)** installed and logged in (a claude.ai
  subscription or an API key both work; no extra Anthropic key is needed)
- **A TypeSafe key** from the [TypeSafe dashboard](https://console.typesafe.ai/keys) — Jev is
  TypeSafe's decision model

## 2. Install

```bash
pip install jev-model-router
```

This installs `jev-claude`, `jev-codex` and `jev-explain`. There are no runtime dependencies.
For the latest development version: `pip install git+https://github.com/himanshu231204/jev_model_routers`.
Optional: `pip install "jev-model-router[typesafe]"` and `JEV_CLIENT=sdk` to call Jev through the
official TypeSafe SDK instead of the built-in stdlib client.

**Or, without a local Python/Node setup**, use the Docker image — it bundles `jev-claude`,
`jev-codex` and the CLIs they wrap:

```bash
docker run -it --rm \
  -e TYPESAFE_API_KEY=your_typesafe_key \
  -v ~/.claude:/home/jev/.claude \
  -v "$PWD":/work \
  ghcr.io/himanshu231204/jev_model_routers        # entrypoint is jev-claude
```

The key goes in as `-e TYPESAFE_API_KEY=...` instead of a file, so you can skip step 3 below.
Mount `~/.claude` so Claude Code's own login persists between runs, and your project directory
at `/work` (the image's working directory). Pass Claude Code arguments after the image name —
they go straight to `jev-claude` — e.g. `... jev_model_routers -p "fix the failing test"`. For
`jev-codex`, add `--entrypoint jev-codex` and mount `~/.codex` instead of `~/.claude`. The image
is built from source and published on tagged releases; see
[`Dockerfile`](../Dockerfile) and [`RELEASE.md`](../RELEASE.md).

## 3. Add your key

`TYPESAFE_API_KEY` is the only variable the router reads. Put it in a file so every terminal has it:

```bash
# Linux / macOS
echo "TYPESAFE_API_KEY=your_typesafe_key" > ~/.jev-router.env

# Windows PowerShell
Set-Content "$HOME\.jev-router.env" "TYPESAFE_API_KEY=your_typesafe_key"
```

It is also read from the environment, `./.env` or `~/.jev-claude.env`. It is sent only to
TypeSafe and never logged. Without it, `jev-claude` prints a notice and starts plain Claude
Code with no routing.

## 4. Use it

```bash
jev-claude                               # interactive Claude Code, routing each new turn
jev-claude -p "fix the failing test"     # print mode; all Claude Code arguments are forwarded
jev-claude --resume                      # sessions, resume and permissions work as usual
```

- The session starts on **JEV Router** (the header shows `jev-router`). It is never saved as
  your default model; plain `claude` is unaffected.
- **Each new message you send** asks Jev once which of your account's models fits (newest
  Haiku / Sonnet / Opus). Everything Claude does to answer that message — file reads, edits,
  commands — stays on that model. Your next message is routed again.
- The **status line** shows the model used for the last turn and Jev's confidence, e.g.
  `claude-haiku-4-5-20251001 (p=0.97) · my-project · 21% context`.
- **`/model` → any real model** turns routing off for the session (status line: `⏸ manual`).
  **`/model` → JEV Router** turns it back on.
- Say it in the prompt to force a tier for one turn: "use opus …", "switch to fast mode …".
  Aliases like fast/strong need "mode", "model" or "tier" after them, so "with long filenames"
  is not read as an override.

The `README.md` has screenshots of each of these steps.

## 5. Understand a decision

```bash
jev-explain <session-id>      # or /jev-explain inside Claude Code, if you've installed the skill
```

Shows the prompt Jev saw, its scores (task complexity, reasoning, tool complexity), the
recommended and selected model, confidence and the policy's reason. The log file has one line per
routed turn:

```text
$ tail ~/.jev-claude.log
[jev] turn=5f877f163e09 decision=haiku model=claude-haiku-4-5-20251001 confidence=0.97 latency=312ms reason=jev ctx~3284
[jev] turn=5f877f163e09 decision=opus model=claude-opus-5-5 confidence=0.97 latency=287ms reason=jev ctx~3773
```

| `reason` | Meaning |
|---|---|
| `jev` | followed Jev's recommendation |
| `override` | your prompt named a tier ("use opus") |
| `jev-unavailable` | Jev failed or timed out; kept the current model (first turn: Opus) |
| `low-confidence-no-downgrade` / `low-confidence-capped` | Jev was unsure; didn't downgrade / capped at Sonnet |
| `downgrade-not-worth-cache-rebuild` | a long conversation isn't downgraded (switching would re-read it all) |
| `…+unavailable` | nearest tier your account has |
| `…/no-change` | the model stayed the same |

## 6. Configuration

| Variable | Effect |
| --- | --- |
| `TYPESAFE_API_KEY` | Required for routing. |
| `JEV_ALLOW_FABLE=1` | Also offer Fable (bills extra usage credits). |
| `JEV_NO_STATUSLINE=1` | Don't add the routing status line. If you already have your own status line, it is kept either way. |
| `JEV_DEBUG=1` | Request-level tracing in the log, including the first 60 characters of each routed prompt. |
| `JEV_CLIENT=sdk` | Use `typesafe-sdk` for the Jev call. |
| `JEV_ENDPOINT` | Point at another System One URL (testing). |

Thresholds (confidence floor, cache-protection size, Jev timeouts) are in
`src/jev_router_live/config.py`.

## 7. Troubleshooting

| Problem | What to check |
|---|---|
| `[jev] no TYPESAFE_API_KEY found` | Add the key (step 3). |
| `[jev] JEV_API_KEY is no longer read - rename it to TYPESAFE_API_KEY` | Earlier versions used `JEV_API_KEY`; rename it in `~/.jev-router.env` (or your environment). |
| Every turn says `reason=jev-unavailable` | The log line above it has the cause (network, HTTP 401 for a bad key, timeout). Claude Code keeps working meanwhile. |
| `[claude-code:unrecognized_model] {"model":"jev-router"}` at startup | Harmless one-line warning from Claude Code; requests are still routed. |
| Status line shows `⏸ manual` | You picked a model in `/model`; pick JEV Router to resume routing. |
| Status line missing | You have your own `statusLine` (kept on purpose), or `JEV_NO_STATUSLINE` is set. |
| Want to see exactly what was sent | `JEV_DEBUG=1 jev-claude`, then read `~/.jev-claude.log`. |

## 8. OpenAI Codex

`jev-codex` works the same way for the Codex CLI (a "Jev Router" entry in Codex's model picker,
a commentary line announcing each decision, `$jev-explain`). It has had less real-session
testing than the Claude Code path.

---

How it works internally: [`ARCHITECTURE.md`](../ARCHITECTURE.md).
