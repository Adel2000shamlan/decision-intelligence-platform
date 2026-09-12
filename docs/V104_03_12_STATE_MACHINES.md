# V104.03.12 — State Machines

## Status
Implemented and verified.

## Scope
A centralized deterministic state-machine layer now defines and validates lifecycle transition graphs for Organization, Project, Risk, and Execution.

## Guarantees
- Explicit allowed transitions only.
- Terminal states are explicit and non-transitionable.
- No dangling transition targets.
- Pure transition evaluation: the machine does not mutate aggregates.
- Existing domain behavior delegates transition legality to the centralized machines.
- Invalid transitions raise `InvalidStateTransition`.
- Existing compatibility helper remains available for earlier callers.

## Verification
The test suite covers graph integrity, terminal behavior, legal/illegal transitions, reuse/non-mutation, and the four implemented aggregate lifecycles.
