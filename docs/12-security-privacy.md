# Security, Privacy, and Auth

> Source: `ARCHITECTURE.md` (§28, §29, §68, §69, §70) — verbatim split, do not edit here; propose changes against the source section.

> Back to index: [docs/README.md](./README.md)

---

# 28. Authentication

The router should avoid becoming the user's credential store.

Preferred pattern:

```text
Agent's credentials
       ↓
existing auth mechanism
       ↓
JEV adapter/proxy forwards auth
```

For provider API-key routing, credentials can be resolved from:

```text
environment
config file
OS credential store
agent-specific auth
external secret manager
```

Never log:

```text
Authorization
API keys
OAuth tokens
cookies
session secrets
full request headers
```

---

---

# 29. Privacy Model

Default data sent to JEV should be the minimum needed for routing.

Recommended:

```text
SEND
✓ user prompt
✓ current model
✓ available model IDs
✓ context token estimate
✓ tool metadata
✓ routing configuration

DO NOT SEND BY DEFAULT
✗ source files
✗ entire repository
✗ API keys
✗ tool outputs
✗ environment secrets
✗ credentials
```

Optional privacy mode:

```bash
JEV_ROUTER_PRIVACY=redacted
```

Possible redaction:

```text
/home/himanshu/project/backend/auth.py
      ↓
<FILE_PATH>
```

---

---

# 68. Security Architecture

Security boundaries:

```text
Agent
  │
  │ potentially sensitive request
  ▼
Adapter
  │
  │ sanitized routing context
  ▼
JEV
```

Never send:

- API keys
- authentication tokens
- cookies
- private keys
- environment variables
- full repository contents unless explicitly enabled

Security modules should include:

```text
redaction
secret detection
request validation
header filtering
local proxy binding
```

---

---

# 69. Local Proxy Security

Default proxy bind:

```text
127.0.0.1
```

Never:

```text
0.0.0.0
```

unless explicitly requested.

Use an ephemeral port:

```text
127.0.0.1:<random-port>
```

The proxy should reject external connections by default.

---

---

# 70. Request Mutation Rules

The router should modify only fields required to apply the routing decision.

Preferred:

```text
model
provider/base URL where necessary
```

Avoid modifying:

```text
tools
messages
permissions
system prompts
MCP configuration
agent control parameters
```

unless a model capability mismatch requires a specific compatibility transformation handled by the adapter.

---
