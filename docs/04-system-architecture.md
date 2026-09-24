# System Architecture

> Source: `ARCHITECTURE.md` (§5, §101, §102) — verbatim split, do not edit here; propose changes against the source section.

> Back to index: [docs/README.md](./README.md)

---

# 5. High-Level System Architecture

```mermaid
flowchart TB
    U[Developer] --> A[AI Coding Agent]

    A --> AD[Agent Adapter]
    AD --> N[Request Normalizer]

    N --> C[Routing Context]
    C --> F[Feature Extractor]
    C --> R[Router Core]

    R --> J[JEV System One]
    J --> JD[JEV Decision]

    JD --> P[Policy Engine]
    P --> MR[Model Resolver]

    MR --> REG[Model Registry]
    REG --> CAP[Capability Matrix]

    MR --> D[Final Routing Decision]
    D --> S[Session / Turn State]
    D --> AD2[Agent Adapter]

    AD2 --> PX[Transport / Proxy]
    PX --> PR[Provider Adapter]
    PR --> API[Model Provider API]

    D --> O[Observability]
    O --> LOG[Structured Logs]
    O --> MET[Metrics]
    O --> EXP[Local Explain API]
```

---

---

# 101. Final Reference Architecture

```mermaid
flowchart LR

    subgraph Agents[AI Coding Agents]
        C[Claude Code]
        X[OpenAI Codex]
        O[OpenCode]
        D[DeepAgents]
        H[Hermes]
        K[Custom Agents]
    end

    subgraph Adapters[Agent Adapter Layer]
        CA[Claude Adapter]
        XA[Codex Adapter]
        OA[OpenCode Adapter]
        DA[DeepAgents Adapter]
        HA[Hermes Adapter]
        KA[Generic Adapter SDK]
    end

    subgraph Core[JEV Model Router Core]
        N[Normalizer]
        R[Router]
        J[JEV Client]
        P[Policy Engine]
        V[Model Resolver]
        S[Session/Turn State]
    end

    subgraph Catalog[Model Intelligence]
        MR[Model Registry]
        CM[Capability Matrix]
        PC[Provider Catalog]
    end

    subgraph Runtime[Runtime Layer]
        T[Transport]
        PR[Provider Adapters]
        OBS[Observability]
        SEC[Security/Redaction]
    end

    subgraph Providers[Model Providers]
        A[Anthropic]
        B[OpenAI]
        G[Google]
        OR[OpenRouter]
        GR[Groq]
        L[Local / Self-hosted]
        CU[Custom]
    end

    C --> CA
    X --> XA
    O --> OA
    D --> DA
    H --> HA
    K --> KA

    CA --> N
    XA --> N
    OA --> N
    DA --> N
    HA --> N
    KA --> N

    N --> R
    R --> J
    J --> P
    P --> V
    V --> MR
    MR --> CM
    MR --> PC
    R --> S
    V --> T
    T --> PR
    PR --> A
    PR --> B
    PR --> G
    PR --> OR
    PR --> GR
    PR --> L
    PR --> CU

    R --> OBS
    T --> SEC
```

---

---

# 102. The Core Abstraction in One Picture

The entire project can be reduced to this contract:

```text
┌──────────────────────────────────────────────────────────┐
│                    AGENT REQUEST                         │
│                                                          │
│ Claude / Codex / OpenCode / DeepAgents / Hermes / Custom │
└───────────────────────────┬──────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────┐
│                  NORMALIZED REQUEST                      │
│                                                          │
│ prompt + context + tools + current model + candidates   │
└───────────────────────────┬──────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────┐
│                         JEV                              │
│                                                          │
│ What level/capability is required for this task?         │
└───────────────────────────┬──────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────┐
│                    POLICY ENGINE                         │
│                                                          │
│ Can we safely apply this decision?                       │
└───────────────────────────┬──────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────┐
│                    MODEL RESOLVER                        │
│                                                          │
│ Which concrete available model satisfies the request?    │
└───────────────────────────┬──────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────┐
│                  TURN STATE / PIN                        │
│                                                          │
│ Keep the selected model stable through the tool loop.    │
└───────────────────────────┬──────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────┐
│                    AGENT ADAPTER                         │
│                                                          │
│ Convert decision back into the agent's native protocol.  │
└───────────────────────────┬──────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────┐
│                  MODEL PROVIDER                          │
└──────────────────────────────────────────────────────────┘
```

---
