# Design Goals and Non-Goals

> Source: `ARCHITECTURE.md` §2-§3 — verbatim split, do not edit here; propose changes against the source section.

> Back to index: [docs/README.md](./README.md)

---

## 2. Design Goals

- **Agent agnostic:** Core router works with any adapter. Adding an agent = new adapter + fixtures + tests. No `if agent == "claude":` in core.
- **Per-turn intelligent routing:** One routing decision per fresh user turn, pinned through the entire tool loop.
- **Provider agnostic:** Supports Anthropic, OpenAI, Google, Groq, OpenRouter, Azure OpenAI, Bedrock, Ollama, LM Studio, custom endpoints.
- **Fail open:** Missing key, timeout, 5xx, or malformed JEV response → fall back to current/default model and record why.
- **Explicit human override:** User model choice always wins over automatic routing.
- **Explainability:** Every routing decision is explainable locally (task complexity, confidence, policy, reason).
- **Privacy-safe:** Never log prompts, keys, or auth headers by default. Send minimum data to JEV.
- **Native agent experience:** Preserve tool execution, permissions, sessions, MCP, streaming, agent-specific commands.

## 3. Non-Goals

JEV does NOT own: filesystem manipulation, code execution, terminal commands, patch generation, repository permissions, MCP server implementation, interactive coding UX, agent memory, task planning.
