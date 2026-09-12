# V104.03 Core Domain Integration Closure

## Purpose
Integrate the previously isolated Decision, Option, and Scenario domain implementations into the unified V104.03 baseline.

## Integrated aggregates
- Organization
- Project
- Decision
- Option
- Scenario
- Risk
- Execution

## Cross-aggregate boundaries
- Option creation requires an existing Decision.
- Scenario creation requires an existing Decision and an Option belonging to that Decision.
- AI-sourced Options must be explicitly `ALTERNATIVE`.
- Selecting an Option does not approve the parent Decision.
- Approving a Scenario does not approve the parent Decision.
- Human actor IDs are required for Decision approval/rejection and Scenario approval.

## Unified gates
All seven aggregate families use the AggregateRoot contract. Decision, Option, and Scenario now participate in centralized state-machine validation, domain rules, aggregate validation, event validation, domain services, and integration tests.

## Verification
The complete test suite is run after integration. No prior placeholder test remains that falsely asserts Decision/Option/Scenario are absent.

## Scope honesty
This closure covers the Core Domain baseline only. It does not claim PostgreSQL persistence, production Event Bus/Outbox/Event Store, authentication, API completion, AI provider integration, agent orchestration, or production deployment.
