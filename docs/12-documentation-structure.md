# Documentation Structure

> Source: `ARCHITECTURE.md` §13 — verbatim split, do not edit here; propose changes against the source section.

> Back to index: [docs/README.md](./README.md)

---

## 13. Documentation Structure

The `docs/` directory contains a verbatim, one-file-per-section split of this architecture
document, plus a standalone quickstart guide:

```
docs/
├── README.md                        # Index and section-to-file map
├── 00-quickstart.md                 # Integration guide, all three strategies (not a §-split)
├── 01-executive-summary.md          # §1  Executive Summary
├── 02-design-goals-and-non-goals.md # §2-§3  Design goals, non-goals
├── 03-core-principle.md             # §4  Core architectural principle
├── 04-system-architecture.md        # §5  High-level system architecture
├── 05-major-components.md           # §6  Major components
├── 06-routing-invariants.md         # §7  Routing invariants (must not regress)
├── 07-architectural-rules.md        # §8  Architectural rules
├── 08-project-structure.md          # §9  Project structure
├── 09-configuration.md              # §10  Configuration
├── 10-testing-rules.md              # §11  Testing rules
├── 11-implementation-phases.md      # §12  Implementation phases
├── 12-documentation-structure.md    # §13  This section
├── 13-success-criterion.md          # §14  Success criterion
└── 14-reference-material.md         # §15  Reference material
```

> **Note:** This file (`ARCHITECTURE.md`) remains the single source of truth. `docs/*` are verbatim splits — do not edit them; propose changes against the source section here.
