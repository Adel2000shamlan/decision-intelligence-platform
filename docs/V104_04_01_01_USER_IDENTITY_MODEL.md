# V104.04.01.01 — User Identity Model

Status: implemented and verified.

## Boundary
This stage defines the authentication user identity only. Credentials,
passwords, tokens, sessions, providers, and authorization are intentionally
excluded and belong to later stages.

## Identity
- UUID aggregate identity.
- Normalized `EmailAddress` value object.
- Validated `Name` value object for display identity.
- Optional bounded `Description` value object.
- Explicit `UserStatus`: active, suspended, archived.
- UTC creation/update timestamps.
- Optimistic version field.
- Initial `UserCreated` domain event.

## Guarantees
- Invalid email/name/status data is rejected at the domain boundary.
- User identity does not store credentials or tokens.
- Creation is deterministic at the domain contract level and emits an event.
- Aggregate invariants validate identity, timestamps, value objects, status, and version.
