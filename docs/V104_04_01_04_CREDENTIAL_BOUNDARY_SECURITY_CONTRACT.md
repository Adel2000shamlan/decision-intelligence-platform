# V104.04.01.04 — Credential Boundary & Security Contract

## Scope
Establishes the hard domain boundary between User identity/lifecycle and credential material.

## Contracts
- User aggregate contains identity and lifecycle data only.
- Passwords, password hashes, salts, tokens, API keys, OTP secrets and private keys are forbidden in User.
- User domain events must not carry credential material.
- SecurityActorContext carries only actor/correlation metadata.
- CredentialStorePort is a future application/infrastructure port; the User aggregate never implements credential storage.

## Enforcement
- Deterministic `CredentialBoundaryContract`.
- `UserCredentialBoundaryRule` integrated into the User RuleSet.
- Aggregate invariant validation enforces the boundary.
- Boundary violations occur before lifecycle mutation and preserve state/version/timestamp.

## Explicit non-scope
Password hashing, credential storage, token issuance/rotation/revocation implementation, authentication APIs and authorization are intentionally deferred to their scheduled stages.
