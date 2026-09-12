# V104.03.10 — Aggregates

## Status
COMPLETED

## Purpose
Establish a framework-independent aggregate-root contract and consistency boundary for the Domain layer without coupling aggregates to FastAPI, SQLAlchemy, PostgreSQL, AI providers, or persistence.

## Implemented
- `AggregateRoot`: stable identity, version, invariant validation, optimistic-version guard.
- `AggregateSnapshot`: immutable application/persistence hand-off container.
- `AggregateBoundary`: side-effect-free invariant validation while preserving pending domain events.
- `AggregateRegistry`: deterministic one-root-per-identity registry for tests/adapters; not a persistence store.
- Organization, Project, Risk, and Execution domain roots explicitly inherit `AggregateRoot`.

## Aggregate Rules
1. Every root has a UUID identity and version >= 1.
2. Root mutations remain inside the root boundary.
3. Domain events remain owned by the root until explicitly pulled.
4. Aggregate validation is framework independent.
5. Version checks reject stale application commands.
6. Registry identity collisions are rejected.
7. Boundary validation must not consume domain events.
8. Aggregate infrastructure is not used as a database or cache.

## Future Integration Contract
Decision, Option, Scenario, and later domain roots must adopt the same `AggregateRoot` contract when their integrated implementations are merged. This stage does not falsely mark those modules as implemented when their source is not present in this baseline artifact.

## Verification
- Full test suite: 83 passed.
- Python compilation: expected to pass before release packaging.
- ZIP integrity: verified after packaging.
