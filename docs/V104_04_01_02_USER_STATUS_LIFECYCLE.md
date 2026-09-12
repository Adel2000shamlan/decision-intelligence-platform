# V104.04.01.02 — User Status & Lifecycle

## Scope
Deterministic lifecycle for the User identity aggregate. Credentials, passwords, sessions and tokens remain outside this stage.

## Lifecycle
- ACTIVE → SUSPENDED
- ACTIVE → ARCHIVED
- SUSPENDED → ACTIVE
- SUSPENDED → ARCHIVED
- ARCHIVED → terminal

## Guarantees
- All legal transitions use the centralized state-machine engine.
- Illegal transitions fail before mutation.
- Lifecycle mutations increment aggregate version.
- Creation remains version 1; the creation event does not represent a state mutation.
- Suspension/reactivation/archive emit immutable domain events.
- Archive is terminal; archived users cannot be renamed or reactivated.
- Expected-version checks protect application-service callers from stale writes.
- Boundary validation preserves pending events.
- No credential/token fields are introduced by this stage.

## Verification
Full regression and lifecycle tests are required before closure.
