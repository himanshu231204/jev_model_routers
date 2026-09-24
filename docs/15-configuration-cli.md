# Configuration and CLI

> Source: `ARCHITECTURE.md` (§6, §53, §54, §61, §62, §63, §64, §73, §79) — verbatim split, do not edit here; propose changes against the source section.

> Back to index: [docs/README.md](./README.md)

---

# 6. Major Components

## 6.1 CLI / Launcher

Responsibilities:

- start the router
- detect available agents
- select adapter
- start local proxy if required
- load configuration
- validate environment
- launch or attach to the selected agent

Possible commands:

```bash
jev-router
jev-router claude
jev-router codex
jev-router opencode
jev-router hermes
jev-router deepagents
```

Optional explicit mode:

```bash
jev-router run --agent claude
jev-router run --agent codex
```

Inspection commands:

```bash
jev-router agents
jev-router models
jev-router status
jev-router explain
jev-router doctor
```

---

---

# 53. Configuration Architecture

Use a layered configuration system.

Recommended precedence:

```text
CLI flag
   ↓
environment variable
   ↓
project config
   ↓
user config
   ↓
defaults
```

Example:

```yaml
router:
  enabled: true
  policy: default
  fail_mode: open

jev:
  timeout_ms: 1500
  deadline_ms: 3000
  max_retries: 1

models:
  allow:
    - anthropic/claude-sonnet
    - anthropic/claude-opus
    - openai/coding-strong

agents:
  auto_detect: true

privacy:
  send_repository_content: false
  log_prompts: false
```

---

---

# 54. Example User Configuration

```yaml
router:
  policy: default
  fail_mode: open

routing:
  min_confidence: 0.30
  max_jev_latency_ms: 1500

models:
  fast: anthropic/claude-haiku
  balanced: anthropic/claude-sonnet
  strong: anthropic/claude-opus

agents:
  claude_code:
    enabled: true
  codex:
    enabled: true
  opencode:
    enabled: true
  hermes:
    enabled: true
  deepagents:
    enabled: true
```

---

---

# 61. Direct Model Mode

Users should be able to disable routing:

```bash
jev-router --no-route
```

or select a model directly:

```bash
jev-router claude --model claude-opus
```

The adapter must then bypass automatic routing for that session or turn.

---

---

# 62. Automatic Agent Detection

Optional:

```bash
jev-router
```

Detection order could be:

```text
explicit CLI choice
    ↓
active environment
    ↓
known process / config detection
    ↓
installed agents
    ↓
interactive selection
```

Example:

```text
Detected:
✓ claude
✓ codex
✓ opencode
✓ hermes

Select agent:
> Claude Code
  OpenAI Codex
  OpenCode
  Hermes
```

---

---

# 63. Doctor Command

A `doctor` command is essential because adapter integrations can break when upstream agents change.

Example:

```text
$ jev-router doctor

JEV Router
──────────
✓ configuration
✓ JEV credentials
✓ Claude Code detected
✓ Codex detected
✓ OpenCode detected
✓ Hermes detected

Agent adapters
──────────────
✓ Claude Code adapter compatible
✓ Codex adapter compatible
! OpenCode adapter requires manual provider configuration
```

---

---

# 64. Compatibility Detection

Each adapter should declare supported versions.

```yaml
claude_code:
  supported:
    min: "2.x"
    tested: "2.x.y"
```

When an unsupported version is detected:

```text
warning
not hard failure
```

The adapter can attempt compatibility mode or passthrough mode.

---

---

# 73. CLI UX

Recommended:

```bash
jev-router claude
```

At startup:

```text
JEV Model Router
────────────────
Agent: Claude Code
Mode: automatic routing
Policy: default
JEV: connected
```

On a routed turn:

```text
[JEV] balanced → strong · confidence 0.92
```

On fallback:

```text
[JEV] unavailable · keeping current model
```

On manual selection:

```text
[JEV] automatic routing paused · manual model selected
```

---

---

# 79. Development Mode

Recommended environment variables:

```bash
JEV_ROUTER_DEBUG=1
JEV_ROUTER_TRACE=1
JEV_ROUTER_DUMP_REQUESTS=1
JEV_ROUTER_LOG_LEVEL=debug
```

Sensitive payloads must require explicit opt-in.

---
