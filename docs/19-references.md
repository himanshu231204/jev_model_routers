# References

> Source: `ARCHITECTURE.md` (§105) — verbatim split, do not edit here; propose changes against the source section.

> Back to index: [docs/README.md](./README.md)

---

# 105. Reference Material

The architecture was designed with the extension mechanisms of current coding-agent ecosystems in mind. In particular:

- OpenCode documents provider configuration and custom `baseURL` support. https://opencode.ai/docs/providers
- Hermes Agent documents provider/model selection, custom providers, and runtime provider resolution. https://github.com/NousResearch/hermes-agent/blob/main/website/docs/developer-guide/adding-providers.md
- The previously inspected `gargpratyush/jev-router` project demonstrates the practical value of per-turn routing, model pinning, fail-open behavior, and CLI-specific proxying. https://github.com/gargpratyush/jev-router

These external interfaces can change. Keep their wire-format logic isolated in the corresponding adapter and compatibility modules.

---
