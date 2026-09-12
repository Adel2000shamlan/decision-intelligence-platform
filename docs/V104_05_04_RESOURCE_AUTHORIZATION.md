# V104.05.04 — Resource Authorization

## Objective
Protect concrete resources after identity/tenant/rule validation and before general policy authorization.

## Ordered implementation stages
1. Resource identity and boundary contract
2. Resource projection and resolution
3. Resource existence and lifecycle gate
4. Tenant/resource binding enforcement
5. Resource-type/permission compatibility
6. Ownership boundary (opt-in when an owner exists)
7. Resource authorization policy contract
8. Deterministic resource policy engine
9. Fail-closed exception handling
10. Authorization service integration
11. Evaluation trace integration
12. Security and resource-boundary tests
13. Full regression verification
14. Production security review
15. Definition of Done
16. Release and closure

## Security semantics
- Missing, nonexistent, suspended/archived resources deny.
- Cross-tenant resources deny.
- Permission resource type must match protected resource type.
- Owner checks apply only to protected actions and only where ownership is explicitly modeled.
- Resource policies cannot manufacture credentials or bypass mandatory authorization rules.
- Policy exceptions fail closed.
- The resource stage is an additional gate; it does not replace human approval or general policy authorization.

## Non-goals
No database persistence, distributed cache, external IAM integration, or production deployment claim is made by this stage.
