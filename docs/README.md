# JEV Model Router — Architecture Docs

> Verbatim, section-for-section split of `ARCHITECTURE.md` (15 sections). `ARCHITECTURE.md`
> remains the single source of truth — these files mirror it and are not edited directly;
> propose changes against the source section in `ARCHITECTURE.md` instead.

## Index

| File | Section | Topic |
|---|---|---|
| [00-quickstart.md](./00-quickstart.md) | — | Integration guide (not a §-split; see its "not yet implemented" notes) |
| [01-executive-summary.md](./01-executive-summary.md) | §1 | Executive summary |
| [02-design-goals-and-non-goals.md](./02-design-goals-and-non-goals.md) | §2-§3 | Design goals, non-goals |
| [03-core-principle.md](./03-core-principle.md) | §4 | Core architectural principle / pipeline contract |
| [04-system-architecture.md](./04-system-architecture.md) | §5 | High-level system architecture |
| [05-major-components.md](./05-major-components.md) | §6 | Major components table |
| [06-routing-invariants.md](./06-routing-invariants.md) | §7 | Routing invariants (must not regress) |
| [07-architectural-rules.md](./07-architectural-rules.md) | §8 | Architectural rules |
| [08-project-structure.md](./08-project-structure.md) | §9 | Project structure, dependency direction |
| [09-configuration.md](./09-configuration.md) | §10 | Configuration precedence and defaults |
| [10-testing-rules.md](./10-testing-rules.md) | §11 | Testing rules |
| [11-implementation-phases.md](./11-implementation-phases.md) | §12 | Implementation phases |
| [12-documentation-structure.md](./12-documentation-structure.md) | §13 | This documentation structure |
| [13-success-criterion.md](./13-success-criterion.md) | §14 | Success criterion |
| [14-reference-material.md](./14-reference-material.md) | §15 | Reference material |

For the current implementation status (what's actually built, not just designed), see
`AGENTS.md` and the root `README.md` — both are kept up to date with `src/` and `tests/`,
while the files in this directory track the architecture document's target design.
