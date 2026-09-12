# V104.03.08 — Execution Domain

## Scope
The Execution Domain turns an approved plan into a controlled execution record and continuously measures delivery health.

## Completed stages
1. Execution aggregate and lifecycle/state machine.
2. Progress tracking.
3. Task tracking and weighted progress.
4. Milestone tracking.
5. Resource consumption tracking.
6. Budget burn tracking.
7. Schedule variance tracking.
8. Performance signals and severity.
9. Deterministic execution-health score and Green/Amber/Red status.
10. Domain events, repository contract, policy service, commands, in-memory adapter and tests.
11. Mutation safety and terminal-state guards.

## Governance boundaries
- Execution completion requires 100% progress.
- Completed, cancelled and archived executions are protected from normal mutation by policy.
- Health is deterministic and explainable; it is not an AI decision authority.
- Signals are observations; they do not silently change the execution state.
- Parent Decision approval remains separate from execution status.

## Health model
Health combines progress, budget, resource consumption, schedule variance, task health and recent signal penalties into a bounded 0–100 score. Green >=80, Amber >=60, Red <60.

## Verification
Run `pytest -q` and `python -m compileall app tests` from the project root.
