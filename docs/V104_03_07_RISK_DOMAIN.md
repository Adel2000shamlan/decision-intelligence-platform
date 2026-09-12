# V104.03.07 — Risk Domain

All stages V104.03.07.01 through .13 are implemented and tested in the current baseline.

## Completion
- Entity: Risk identity, project/decision relation, source, inherent/residual ratings.
- Lifecycle: DRAFT → IDENTIFIED → ASSESSED → MITIGATING → MONITORED/ACCEPTED → CLOSED → ARCHIVED.
- Rules: 1–5 probability/impact ratings, deterministic score and level, residual-risk guard, terminal archive state, versioning, source tracking.
- Validation: structural and business checks are separated.
- Commands: create, identify, assess, start mitigation, monitor, accept, close, archive, rename.
- Events: created, identified, assessed, mitigation started, monitored, accepted, closed, archived, updated.
- Aggregate boundary, repository contract, policy service, errors, tests, and infrastructure-boundary checks are included.
