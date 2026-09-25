# JEV Model Router

> An agent-agnostic intelligent model routing layer for AI coding agents.

[![Python](https://img.shields.io/badge/Python-%3E%3D3.11-blue)]()
[![License](https://img.shields.io/badge/License-MIT-green)]()
[![Status](https://img.shields.io/badge/Status-Development-blue)]()

---

## What Is This?

JEV Model Router sits between your coding agent (Claude Code, Codex, OpenCode, and others) and the AI models they use.

Instead of forcing every coding task onto a single model, it uses the **JEV API** to pick the best available model for each task — automatically.

```mermaid
graph LR
    A["Coding Agent<br/>Claude Code · Codex · OpenCode"] --> B["JEV Model Router<br/>Normalize → Ask → Policy → Resolve"]
    B --> C["Models<br/>(Claude, OpenAI, Gemini…)"]
```

**Why?** A simple README edit doesn't need the strongest model. A complex architectural refactor does. JEV makes that decision per turn, so you always get the right model without changing how you work.

---

## Quick Start

### 1. Install

```bash
pip install -e .
```

Or install from PyPI when available:

```bash
pip install jev-router
```

### 2. Set Your JEV API Key

`jev/client.py` calls TypeSafe's Jev decision model via TypeSafe's System One API
(`https://api.typesafe.ai/v1/systemone`), so `TYPESAFE_API_KEY` should be a
[TypeSafe](https://typesafe.ai/) API key.

```bash
# Linux / macOS
export TYPESAFE_API_KEY="your_typesafe_api_key"

# Windows PowerShell
$env:TYPESAFE_API_KEY="your_typesafe_api_key"
```

> 🔒 Never commit or share your API key. Use `.env`, OS secret managers, or CI/CD secret stores.

### 3. Run

```bash
jev-router run --agent claude_code --prompt "add input validation to the login form"
```

This makes one JEV routing decision for the session — using `--prompt` as the signal — then
launches `claude` with that model applied. `--agent` defaults to `claude_code`; run
`jev-router agents` to see every registered adapter and whether it's detected on your machine.
Omitting `--prompt` gives JEV nothing to route on, so it typically falls back to the current/
default model instead of picking one.

For the full integration guide, see [`docs/quickstart.md`](docs/quickstart.md).

### Per-turn routing (live proxy)

The `jev-router run` command above makes one routing decision at session start. For routing
**every fresh turn** of a Claude Code or Codex session — not just the first one — use the live
proxy tools instead:

```bash
echo "JEV_API_KEY=..." > ~/.jev-router.env   # a TypeSafe key; JEV_API_KEY is the only variable read

jev-claude               # launches Claude Code, routing each new user turn
jev-codex                 # launches OpenAI Codex, routing each new user turn
jev-explain <session-id>  # shows why the last turn was routed the way it was
```

These wrap the real `claude`/`codex` CLIs with a local HTTP proxy in front of their API, so a
session's tools, permissions, sessions (`/resume`), authentication and streaming are untouched
— only the model picked for each fresh turn changes. In Claude Code:

- **`/model` → "JEV Router"** (selected by default) routes each new turn: JEV is asked once per
  turn, picks from your account's own models (newest Haiku / Sonnet / Opus), and that model is
  pinned for the turn's whole tool loop.
- **`/model` → any real model** turns routing off; requests pass through untouched. Selecting
  "JEV Router" again turns it back on.
- **JEV unavailable** (no key, timeout, error): Claude Code keeps working on a safe fallback
  (Opus); nothing blocks.
- Each decision is logged as one safe line (model, confidence, latency, reason — no prompt) in
  `~/.jev-claude.log`; `JEV_DEBUG=1` adds request-level tracing.

See [`src/jev_router_live/README.md`](src/jev_router_live/README.md) and
[`ARCHITECTURE.md`](ARCHITECTURE.md) §16 for how it works, debugging, and known limitations.

---

## How It Works

Every coding request goes through a simple pipeline:

```mermaid
flowchart TD
    A[Agent Request] --> B["Adapter (agent-specific)"]
    B --> C["Normalized Request (common format)"]
    C --> D["JEV API (asks: what model should I use?)"]
    D --> E["Policy Engine (rules, confidence checks, overrides)"]
    E --> F["Model Resolver (picks the concrete model)"]
    F --> G["Provider / Model (execution)"]
```

### Key Principles

| Principle | What it means |
|---|---|
| **Agent-agnostic** | Works with Claude Code, Codex, OpenCode, DeepAgents, Hermes — and any future agent via adapters |
| **One decision per turn** | Routes once per user turn; the rest of the tool loop reuses the selected model |
| **Explicit overrides win** | If a user manually picks a model, that choice always wins |
| **Fail open** | If JEV is unavailable, the router falls back to the current/default model — coding never stops |
| **No secrets in logs** | API keys, prompts, and auth headers are never logged |

---

## Installation

### Prerequisites

- **Python ≥ 3.11**
- **A [TypeSafe](https://typesafe.ai/) API key** (used as `TYPESAFE_API_KEY` to reach TypeSafe's Jev model)

### From Source

```bash
git clone https://github.com/himanshu231204/jev_model_routers.git
cd jev_model_routers
pip install -e .
```

### Verify

```bash
jev-router --help
```

---

## Configuration

Config is managed via YAML files. The default config is at `configs/default.yaml`:

```yaml
router:
  enabled: true
  policy: default
  fail_mode: open       # routing failure → continue with current model

jev:
  timeout_ms: 1500      # keep calls short — routing is on the hot path
  deadline_ms: 3000
  max_retries: 1

models:
  allow:
    - anthropic/claude-fable   # fast tier
    - anthropic/claude-haiku   # fast tier (alternate)
    - anthropic/claude-sonnet  # balanced tier
    - anthropic/claude-opus    # strong tier
    - openai/coding-strong     # strong tier (codex/opencode/hermes only)

agents:
  auto_detect: true
```

Config precedence: **CLI args → environment variables → project config → user config → defaults**.

---

## Adapters

Each coding agent gets its own adapter — the core router never changes.

| Agent | Status |
|---|---|
| Claude Code | 🟢 Implemented |
| OpenAI Codex | 🟢 Implemented |
| OpenCode | 🟢 Implemented |
| DeepAgents | 🟢 Implemented |
| Hermes | 🟢 Implemented |

Adding a new adapter requires only:
1. Create the adapter module
2. Normalize the native request
3. Implement model application
4. Add tests

No changes to the core router, policy, JEV auth, or state layer needed.

---

## Command Line

```bash
jev-router run --agent <name>  # Route once at session start, launch the agent (default: claude_code)
jev-router agents              # List registered adapters and detection status
jev-router models              # Show the configured model catalog
jev-router status              # Show current routing state (enabled/passthrough)
jev-router explain             # Explain the last routing decision
jev-router doctor              # Diagnose environment/config (Python version, key presence)

jev-claude                     # Launch Claude Code with per-turn (live proxy) routing
jev-codex                      # Launch OpenAI Codex with per-turn (live proxy) routing
jev-explain <session-id>       # Explain the live proxy's last routing decision
```

Passthrough (no routing) happens automatically whenever the key is unset — `TYPESAFE_API_KEY`
for `jev-router run`, `JEV_API_KEY` (only) for `jev-claude`/`jev-codex`. There's no separate
flag for it.

---

## Development

```bash
# Install in development mode, with pytest
pip install -e ".[test]"

# Run all tests
python -m pytest

# Run tests for a specific module
python -m pytest tests/unit/test_policy.py
```

### Project Structure

```
src/jev_router/
├── cli/          # Command-line interface
├── core/         # Router, policy, resolver
├── contracts/    # NormalizedRequest, ModelSpec types
├── adapters/     # Agent-specific adapters
├── providers/    # Provider integrations
├── jev/          # JEV API client
├── transport/    # HTTP/SSE/WS forwarding
├── state/        # Per-turn/session persistence
├── config/       # Runtime configuration
├── security/     # Secrets/redaction
└── observability/# Logs, metrics, explanations

src/jev_router_live/   # Per-turn live proxy routing (independent of jev_router above)
├── config.py     # Tiers, thresholds, override phrases, Jev questions
├── policy.py     # Pure routing decision function
├── router.py     # Jev/System One HTTP call
├── proxy.py      # Claude Code per-turn proxy
├── codex_proxy.py# Codex per-turn proxy
├── status.py     # Per-session decision file
├── explain.py    # Explanation report renderer
├── settings.py   # Saved-default-model restore
└── bin/          # jev-claude / jev-codex / jev-statusline / jev-explain entry points
```

---

## Contributing

Contributions should preserve the core architecture:

> **Agents adapt to the router. The router should not become agent-specific.**

When adding a new integration, prefer a new adapter over adding agent-specific branches to the routing core. See `ARCHITECTURE.md` for the full design.

---

## License

[MIT](LICENSE)
