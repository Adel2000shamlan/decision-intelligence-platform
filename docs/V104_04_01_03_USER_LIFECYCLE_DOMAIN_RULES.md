# V104.04.01.03 — User Lifecycle Domain Rules & Invariants

## Scope
Deterministic domain rules and invariants for the User aggregate lifecycle.

## Implemented
- User identity integrity rule.
- User lifecycle status rule.
- Explicit transition source rules for suspend/reactivate/archive.
- Archived terminal mutation rule.
- RuleSet integration into User aggregate validation.
- Service-level pre-mutation rule evaluation for lifecycle commands.
- Mutation-safety regression test: rejected lifecycle commands do not change state/version/timestamp.

## Boundary
Rules are deterministic and infrastructure-independent. Authentication credentials, password policy, tokens, persistence, authorization, and external identity providers remain outside this step.

## Definition of Done
- Rules are deterministic and side-effect free.
- Illegal lifecycle transitions are rejected before mutation at the service boundary.
- Aggregate invariants remain enforced.
- Full regression suite passes.
- Python compilation succeeds.
- Release archive passes ZIP integrity validation.
