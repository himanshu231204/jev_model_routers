# Transport, Proxy, and Performance

> Source: `ARCHITECTURE.md` (§26, §27, §71, §72, §80) — verbatim split, do not edit here; propose changes against the source section.

> Back to index: [docs/README.md](./README.md)

---

# 26. Transport Layer

The transport layer is responsible for forwarding requests without becoming a second agent.

```text
Adapter
  ↓
Transport
  ├── HTTP
  ├── HTTPS
  ├── SSE
  ├── WebSocket if required
  └── local process/SDK
```

Recommended internal interface:

```python
class Transport(Protocol):
    async def send(self, request) -> Response:
        ...
```

---

---

# 27. Proxy Architecture

When using reverse proxy mode:

```text
               localhost

┌──────────────┐
│ Coding Agent │
└──────┬───────┘
       │
       │ provider request
       ▼
┌─────────────────────────┐
│  JEV Local Proxy        │
│                         │
│  parse request          │
│  identify new turn      │
│  normalize              │
│  route                  │
│  rewrite model          │
│  forward                │
└──────────┬──────────────┘
           │
           ▼
┌─────────────────────────┐
│ Provider API            │
└─────────────────────────┘
```

The proxy should be:

- localhost-only by default
- ephemeral by default
- credential-preserving
- streaming-aware
- low-latency
- fail-safe

---

---

# 71. Streaming Architecture

Streaming should be transparent.

```text
Provider
   ↓ SSE chunks
Transport
   ↓
Adapter
   ↓
Agent
```

The router should not buffer an entire response unless it needs to inspect a protocol event.

Routing is decided **before** streaming starts.

---

---

# 72. WebSocket Support

Do not make WebSocket support a first-class requirement in V1.

Build the transport abstraction so it can support:

```text
HTTP
SSE
WebSocket
```

but implement only what an adapter actually needs.

---

---

# 80. Performance Architecture

Target routing overhead:

```text
warm JEV call: low hundreds of ms target
cold JEV call: bounded by hard deadline
```

The router should optimize for:

```text
minimal serialization
minimal local proxy overhead
connection reuse
async I/O
no unnecessary buffering
no repeated routing during tool loops
```

---
