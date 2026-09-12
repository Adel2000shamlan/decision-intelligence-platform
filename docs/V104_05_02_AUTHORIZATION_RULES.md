# V104.05.02 — Authorization Rules

## Scope
This stage establishes deterministic authorization safety rules between the V104.05.01 foundation and later policy/RBAC stages.

## Closed sequence
1. Allow/Deny rule model.
2. Default-deny/fail-closed behavior.
3. Explicit permission requirement contract.
4. Sensitive-action protection.
5. Identity/actor consistency.
6. Tenant/resource binding consistency.
7. Permission/resource compatibility.
8. Deterministic rule evaluation and enforcement.
9. Boundary and abuse tests.
10. Definition of Done and release closure.

## Security decisions
- A rule can only allow what its contract explicitly permits; it cannot invent a grant.
- Any mandatory rule failure produces DENY.
- Sensitive actions (`approve`, `reject`, `execute`, `archive`, `delete`) require a human actor and strong authentication assurance.
- AI/system actors cannot satisfy the sensitive-action human gate.
- Resource type and permission resource must match.
- Tenant context must match the protected resource tenant.
- Explicit grants remain distinct from mandatory safety rules and are intentionally not merged with RBAC.
