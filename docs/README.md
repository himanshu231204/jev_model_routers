# JEV Model Router — Architecture Docs

> Split from `ARCHITECTURE.md` (106 sections, verbatim). `ARCHITECTURE.md` remains the source of truth and is left untouched.

# JEV Model Router — Complete Architecture

> **Status:** Target architecture / implementation blueprint  
> **Project:** `jev_model_router`  
> **Primary goal:** Build an agent-agnostic model router that can sit in front of coding agents such as Claude Code, OpenAI Codex, OpenCode, DeepAgents-based coding agents, Hermes Agent, and future/custom agents.

---


## Index

| File | Sections | Topics |
|---|---|---|
| [00-quickstart.md](./00-quickstart.md) | — | Integration guide, all three strategies |
| [01-overview.md](./01-overview.md) | §1 | Executive Summary |
| [02-design-goals.md](./02-design-goals.md) | §2, §3 | Design goals, non-goals |
| [03-core-principles.md](./03-core-principles.md) | §4, §100, §106 | Core principle, architectural rules, final principle |
| [04-system-architecture.md](./04-system-architecture.md) | §5, §101, §102 | System diagram, final reference arch, core abstraction |
| [05-agent-adapters.md](./05-agent-adapters.md) | §7, §8, §9, §33, §34, §35, §36, §37, §38, §39, §40 | Adapter layer, types, strategy, capability contract, per-agent examples, SDK, plugins |
| [06-request-models.md](./06-request-models.md) | §10, §11, §12, §13 | Normalized request, repo context, tool metadata, routing context |
| [07-router-core.md](./07-router-core.md) | §14, §15, §16, §87, §88, §89 | Router core, JEV decision contract, capability routing, internal/adapter flows |
| [08-models-registry.md](./08-models-registry.md) | §17, §18, §19, §83, §84, §85, §86 | Registry, resolution, catalog discovery, exact-vs-tier, capability matrix, formula |
| [09-policy-engine.md](./09-policy-engine.md) | §20, §21, §22, §46, §47, §48, §49, §60 | Policy engine, overrides, confidence, policy profiles, cost/latency/cache, switch guard |
| [10-turn-state.md](./10-turn-state.md) | §23, §24, §25, §41, §42, §43, §44, §45, §81, §82 | Turn pinning, sub-agent isolation, context-aware routing, session store, lifecycle, classification, concurrency, worktrees |
| [11-transport-proxy.md](./11-transport-proxy.md) | §26, §27, §71, §72, §80 | Transport, proxy, streaming, WebSocket, performance |
| [12-security-privacy.md](./12-security-privacy.md) | §28, §29, §68, §69, §70 | Auth, privacy model, security arch, proxy security, mutation rules |
| [13-failure-handling.md](./13-failure-handling.md) | §30, §31, §32, §77, §78 | Failure hierarchy, fallback matrix, compatibility validation, error taxonomy |
| [14-observability.md](./14-observability.md) | §50, §51, §52, §74, §75, §76 | Observability events, privacy-safe logging, explain command/API, metrics, lifecycle |
| [15-configuration-cli.md](./15-configuration-cli.md) | §6, §53, §54, §61, §62, §63, §64, §73, §79 | CLI/launcher, config arch, example config, direct mode, detection, doctor, compat, UX, dev mode |
| [16-project-structure.md](./16-project-structure.md) | §55, §56, §57, §90, §91, §92, §93, §94 | Project layout, dependencies, contracts, plugins, versioning, compat layer, docs, README |
| [17-testing.md](./17-testing.md) | §65, §66, §67 | Unit, contract, fixtures |
| [18-roadmap.md](./18-roadmap.md) | §58, §59, §95, §96, §97, §98, §99, §103, §104 | Routing examples, V1/V2/V3 scope, phases, acceptance, first commit, success criterion |
| [19-references.md](./19-references.md) | §105 | Reference material |

## Section-to-file map (all 106 sections)

- §1 `## 1. Executive Summary` → [01-overview.md](./01-overview.md)
- §2 `# 2. Design Goals` → [02-design-goals.md](./02-design-goals.md)
- §3 `# 3. Non-Goals` → [02-design-goals.md](./02-design-goals.md)
- §4 `# 4. Core Architectural Principle` → [03-core-principles.md](./03-core-principles.md)
- §5 `# 5. High-Level System Architecture` → [04-system-architecture.md](./04-system-architecture.md)
- §6 `# 6. Major Components` → [15-configuration-cli.md](./15-configuration-cli.md)
- §7 `# 7. Agent Adapter Layer` → [05-agent-adapters.md](./05-agent-adapters.md)
- §8 `# 8. Agent Adapter Types` → [05-agent-adapters.md](./05-agent-adapters.md)
- §9 `# 9. Supported Agent Strategy` → [05-agent-adapters.md](./05-agent-adapters.md)
- §10 `# 10. Normalized Request Model` → [06-request-models.md](./06-request-models.md)
- §11 `# 11. Repository Context` → [06-request-models.md](./06-request-models.md)
- §12 `# 12. Tool Metadata` → [06-request-models.md](./06-request-models.md)
- §13 `# 13. Routing Context` → [06-request-models.md](./06-request-models.md)
- §14 `# 14. JEV Router Core` → [07-router-core.md](./07-router-core.md)
- §15 `# 15. JEV Decision Contract` → [07-router-core.md](./07-router-core.md)
- §16 `# 16. Capability-Based Routing` → [07-router-core.md](./07-router-core.md)
- §17 `# 17. Model Registry` → [08-models-registry.md](./08-models-registry.md)
- §18 `# 18. Model Resolution` → [08-models-registry.md](./08-models-registry.md)
- §19 `# 19. Model Resolution Example` → [08-models-registry.md](./08-models-registry.md)
- §20 `# 20. Routing Policy Engine` → [09-policy-engine.md](./09-policy-engine.md)
- §21 `# 21. Explicit Overrides` → [09-policy-engine.md](./09-policy-engine.md)
- §22 `# 22. Confidence Policy` → [09-policy-engine.md](./09-policy-engine.md)
- §23 `# 23. Turn Pinning` → [10-turn-state.md](./10-turn-state.md)
- §24 `# 24. Conversation / Sub-Agent Isolation` → [10-turn-state.md](./10-turn-state.md)
- §25 `# 25. Context-Aware Routing` → [10-turn-state.md](./10-turn-state.md)
- §26 `# 26. Transport Layer` → [11-transport-proxy.md](./11-transport-proxy.md)
- §27 `# 27. Proxy Architecture` → [11-transport-proxy.md](./11-transport-proxy.md)
- §28 `# 28. Authentication` → [12-security-privacy.md](./12-security-privacy.md)
- §29 `# 29. Privacy Model` → [12-security-privacy.md](./12-security-privacy.md)
- §30 `# 30. Failure Handling` → [13-failure-handling.md](./13-failure-handling.md)
- §31 `# 31. Fallback Matrix` → [13-failure-handling.md](./13-failure-handling.md)
- §32 `# 32. Model Compatibility Validation` → [13-failure-handling.md](./13-failure-handling.md)
- §33 `# 33. Agent Capability Contract` → [05-agent-adapters.md](./05-agent-adapters.md)
- §34 `# 34. Agent Adapter Example: Claude Code` → [05-agent-adapters.md](./05-agent-adapters.md)
- §35 `# 35. Agent Adapter Example: OpenAI Codex` → [05-agent-adapters.md](./05-agent-adapters.md)
- §36 `# 36. Agent Adapter Example: OpenCode` → [05-agent-adapters.md](./05-agent-adapters.md)
- §37 `# 37. Agent Adapter Example: DeepAgents` → [05-agent-adapters.md](./05-agent-adapters.md)
- §38 `# 38. Agent Adapter Example: Hermes` → [05-agent-adapters.md](./05-agent-adapters.md)
- §39 `# 39. Generic Adapter SDK` → [05-agent-adapters.md](./05-agent-adapters.md)
- §40 `# 40. Plugin Architecture` → [05-agent-adapters.md](./05-agent-adapters.md)
- §41 `# 41. Session State Store` → [10-turn-state.md](./10-turn-state.md)
- §42 `# 42. Turn Lifecycle` → [10-turn-state.md](./10-turn-state.md)
- §43 `# 43. Request Classification` → [10-turn-state.md](./10-turn-state.md)
- §44 `# 44. Auxiliary Calls` → [10-turn-state.md](./10-turn-state.md)
- §45 `# 45. Sub-Agent Routing` → [10-turn-state.md](./10-turn-state.md)
- §46 `# 46. Routing Policies` → [09-policy-engine.md](./09-policy-engine.md)
- §47 `# 47. Cost Policy` → [09-policy-engine.md](./09-policy-engine.md)
- §48 `# 48. Latency Policy` → [09-policy-engine.md](./09-policy-engine.md)
- §49 `# 49. Caching JEV Decisions` → [09-policy-engine.md](./09-policy-engine.md)
- §50 `# 50. Observability Architecture` → [14-observability.md](./14-observability.md)
- §51 `# 51. Privacy-Safe Logging` → [14-observability.md](./14-observability.md)
- §52 `# 52. Explain Command` → [14-observability.md](./14-observability.md)
- §53 `# 53. Configuration Architecture` → [15-configuration-cli.md](./15-configuration-cli.md)
- §54 `# 54. Example User Configuration` → [15-configuration-cli.md](./15-configuration-cli.md)
- §55 `# 55. Project Structure` → [16-project-structure.md](./16-project-structure.md)
- §56 `# 56. Dependency Direction` → [16-project-structure.md](./16-project-structure.md)
- §57 `# 57. Interface Contracts` → [16-project-structure.md](./16-project-structure.md)
- §58 `# 58. End-to-End Routing Example` → [18-roadmap.md](./18-roadmap.md)
- §59 `# 59. Simple Task Example` → [18-roadmap.md](./18-roadmap.md)
- §60 `# 60. Model Switch Guard` → [09-policy-engine.md](./09-policy-engine.md)
- §61 `# 61. Direct Model Mode` → [15-configuration-cli.md](./15-configuration-cli.md)
- §62 `# 62. Automatic Agent Detection` → [15-configuration-cli.md](./15-configuration-cli.md)
- §63 `# 63. Doctor Command` → [15-configuration-cli.md](./15-configuration-cli.md)
- §64 `# 64. Compatibility Detection` → [15-configuration-cli.md](./15-configuration-cli.md)
- §65 `# 65. Testing Architecture` → [17-testing.md](./17-testing.md)
- §66 `# 66. Contract Test Example` → [17-testing.md](./17-testing.md)
- §67 `# 67. Golden Fixtures` → [17-testing.md](./17-testing.md)
- §68 `# 68. Security Architecture` → [12-security-privacy.md](./12-security-privacy.md)
- §69 `# 69. Local Proxy Security` → [12-security-privacy.md](./12-security-privacy.md)
- §70 `# 70. Request Mutation Rules` → [12-security-privacy.md](./12-security-privacy.md)
- §71 `# 71. Streaming Architecture` → [11-transport-proxy.md](./11-transport-proxy.md)
- §72 `# 72. WebSocket Support` → [11-transport-proxy.md](./11-transport-proxy.md)
- §73 `# 73. CLI UX` → [15-configuration-cli.md](./15-configuration-cli.md)
- §74 `# 74. Explanation API` → [14-observability.md](./14-observability.md)
- §75 `# 75. Telemetry Metrics` → [14-observability.md](./14-observability.md)
- §76 `# 76. Decision Event Lifecycle` → [14-observability.md](./14-observability.md)
- §77 `# 77. Error Taxonomy` → [13-failure-handling.md](./13-failure-handling.md)
- §78 `# 78. Error Handling Rule` → [13-failure-handling.md](./13-failure-handling.md)
- §79 `# 79. Development Mode` → [15-configuration-cli.md](./15-configuration-cli.md)
- §80 `# 80. Performance Architecture` → [11-transport-proxy.md](./11-transport-proxy.md)
- §81 `# 81. Concurrency` → [10-turn-state.md](./10-turn-state.md)
- §82 `# 82. Multi-Agent Worktree Isolation` → [10-turn-state.md](./10-turn-state.md)
- §83 `# 83. Model Availability Discovery` → [08-models-registry.md](./08-models-registry.md)
- §84 `# 84. Exact Model vs Tier` → [08-models-registry.md](./08-models-registry.md)
- §85 `# 85. Model Capability Matrix` → [08-models-registry.md](./08-models-registry.md)
- §86 `# 86. Routing Formula` → [08-models-registry.md](./08-models-registry.md)
- §87 `# 87. Recommended Internal Flow` → [07-router-core.md](./07-router-core.md)
- §88 `# 88. Adapter Flow` → [07-router-core.md](./07-router-core.md)
- §89 `# 89. What Belongs in Core vs Adapter` → [07-router-core.md](./07-router-core.md)
- §90 `# 90. Example Future Plugin` → [16-project-structure.md](./16-project-structure.md)
- §91 `# 91. Versioning Strategy` → [16-project-structure.md](./16-project-structure.md)
- §92 `# 92. Compatibility Layer` → [16-project-structure.md](./16-project-structure.md)
- §93 `# 93. Documentation Structure` → [16-project-structure.md](./16-project-structure.md)
- §94 `# 94. README Positioning` → [16-project-structure.md](./16-project-structure.md)
- §95 `# 95. V1 Implementation Scope` → [18-roadmap.md](./18-roadmap.md)
- §96 `# 96. V2 Scope` → [18-roadmap.md](./18-roadmap.md)
- §97 `# 97. V3 Scope` → [18-roadmap.md](./18-roadmap.md)
- §98 `# 98. Implementation Phases` → [18-roadmap.md](./18-roadmap.md)
- §99 `# 99. Acceptance Criteria` → [18-roadmap.md](./18-roadmap.md)
- §100 `# 100. Architectural Rules — Keep These Strict` → [03-core-principles.md](./03-core-principles.md)
- §101 `# 101. Final Reference Architecture` → [04-system-architecture.md](./04-system-architecture.md)
- §102 `# 102. The Core Abstraction in One Picture` → [04-system-architecture.md](./04-system-architecture.md)
- §103 `# 103. Recommended First Commit Structure` → [18-roadmap.md](./18-roadmap.md)
- §104 `# 104. Architectural Success Criterion` → [18-roadmap.md](./18-roadmap.md)
- §105 `# 105. Reference Material` → [19-references.md](./19-references.md)
- §106 `# 106. Final Principle` → [03-core-principles.md](./03-core-principles.md)
