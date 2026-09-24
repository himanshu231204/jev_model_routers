# JEV Model Router

> An agent-agnostic intelligent model routing layer for AI coding agents.

[![Python](https://img.shields.io/badge/Python-%3E%3D3.11-blue)]()
[![License](https://img.shields.io/badge/License-MIT-green)]()
[![Status](https://img.shields.io/badge/Status-Development-blue)]()

---

## What Is This?

JEV Model Router sits between your coding agent (Claude Code, Codex, OpenCode, and others) and the AI models they use.

Instead of forcing every coding task onto a single model, it uses the **JEV API** to pick the best available model for each task — automatically.

```
 ┌──────────────┐       ┌──────────────────┐       ┌──────────────┐
 │  Coding Agent │──────▶│  JEV Model Router │──────▶│   Models     │
 │               │       │                   │       │  (Claude,    │
 │  Claude Code  │       │  Normalize → Ask  │       │   OpenAI,    │
 │  Codex        │       │  Policy → Resolve │       │   Gemini…)   │
 │  OpenCode     │       │                   │       │              │
 └──────────────┘       └──────────────────┘       └──────────────┘
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

```bash
# Linux / macOS
export JEV_API_KEY="your_jev_api_key"

# Windows PowerShell
$env:JEV_API_KEY="your_jev_api_key"
```

> 🔒 Never commit or share your API key. Use `.env`, OS secret managers, or CI/CD secret stores.

### 3. Run

```bash
jev-router
```

That's it — the router starts and begins intercepting requests, routing each one through JEV.

---

## How It Works

Every coding request goes through a simple pipeline:

```
Agent Request
      │
      ▼
Adapter (agent-specific)
      │
      ▼
Normalized Request  (common format)
      │
      ▼
JEV API  (asks: what model should I use?)
      │
      ▼
Policy Engine  (applies rules, confidence checks, overrides)
      │
      ▼
Model Resolver  (picks the concrete model)
      │
      ▼
Provider / Model  (execution)
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
- **JEV API key** (sign up at [JEV](https://jev.ai))

### From Source

```bash
git clone https://github.com/your-org/jev_model_routers.git
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
    - anthropic/claude-sonnet
    - anthropic/claude-opus
    - openai/coding-strong

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
jev-router                    # Start the router
jev-router --config path.yaml # Use a specific config file
jev-router --no-routing       # Passthrough mode (no routing)
```

---

## Development

```bash
# Run all tests
python -m pytest

# Run tests for a specific module
python -m pytest tests/unit/test_policy.py

# Install in development mode
pip install -e .
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
```

---

## Roadmap

### Phase 1 — Core Router
- [x] JEV API client
- [x] Normalized request schema
- [x] Policy engine
- [x] Model registry
- [x] Session/turn state
- [x] Fallback behavior
- [x] Unit tests

### Phase 2 — First Agent Adapters
- [x] Claude Code
- [x] Codex
- [x] OpenCode

### Phase 3 — SDK-Based Agents
- [x] DeepAgents
- [x] Hermes
- [ ] Generic SDK adapter interface

### Phase 4 — Developer Experience
- [x] CLI
- [x] Configuration file
- [x] Routing explanation
- [x] Structured logs
- [ ] Debug mode

### Phase 5 — Advanced Routing
- [ ] Context-aware routing
- [ ] Cost-aware routing
- [ ] Latency-aware routing
- [ ] Routing analytics

---

## Contributing

Contributions should preserve the core architecture:

> **Agents adapt to the router. The router should not become agent-specific.**

When adding a new integration, prefer a new adapter over adding agent-specific branches to the routing core. See `ARCHITECTURE.md` for the full design.

---

## License

[MIT](LICENSE)
