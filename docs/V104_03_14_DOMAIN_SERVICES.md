# V104.03.14 — Domain Services

## Scope
Deterministic, framework-independent domain orchestration services for the implemented Organization, Project, Risk, and Execution domains.

## Guarantees
- Services coordinate aggregates and repositories without embedding infrastructure concerns.
- Entity/aggregate invariants remain authoritative; services do not bypass them.
- Cross-aggregate policies are enforced before persistence.
- Optimistic version checks are supported where an aggregate exposes `assert_version`.
- Returned `ServiceResult` contains the mutated aggregate and its domain events after the service consumes the pending event queue.
- Missing aggregates fail explicitly with `EntityNotFound`.
- Services do not publish events or perform external side effects; publication remains an application/infrastructure concern.

## Boundary
This stage does not claim transactions, Unit of Work, message buses, retries, persistence adapters, or external integrations. Those belong to later application/infrastructure stages.
