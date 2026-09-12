# V104.03.17 — Core Domain Definition of Done

Status: COMPLETED for the integrated domain baseline.

## Mandatory gates
- [x] Domain foundation exists and is framework-independent.
- [x] Organization, Project, Risk and Execution aggregates implement the shared aggregate contract.
- [x] Value Objects are immutable and validated.
- [x] Domain Rules are deterministic and wired to invariants.
- [x] State Machines are centralized and graphs are validated.
- [x] Domain Events have identity, timestamp, aggregate identity and metadata/envelope support.
- [x] Domain Services coordinate domain behavior without infrastructure side effects.
- [x] Domain Validation is deterministic and side-effect free.
- [x] Domain Tests cover success paths, failure paths, boundaries, concurrency and mutation safety.
- [x] Static syntax/AST checks pass.
- [x] Full pytest suite passes.
- [x] Python compileall passes.
- [x] Artifact ZIP integrity is checked before release.

## Explicit non-goals
This DoD does not claim completion of PostgreSQL persistence, authentication, production API, event bus/outbox/event store, AI, agents, knowledge retrieval, frontend production PWA, deployment or production operations.

## Integration boundary
Decision/Option/Scenario were implemented in earlier separate domain artifacts but are not present as integrated roots in the V104.03.14-derived baseline used to close V104.03.15–V104.03.17. Therefore those three modules are intentionally not marked as integrated Core Domain implementation in this artifact. Their future merge must rerun the same validation, test and DoD gates.
