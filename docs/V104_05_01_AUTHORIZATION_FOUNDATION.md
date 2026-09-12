# V104.05.01 — Authorization Foundation

Status: **CLOSED / COMPLETE**

## Scope
This stage establishes the authorization-domain foundation only. It does not implement roles, permission administration, tenant membership policy, resource-specific rules, API enforcement, or production persistence; those belong to later roadmap stages.

## Completed substeps
1. Permission Model — immutable `Permission` with canonical `resource:action` key.
2. Resource Model — immutable `Resource` with typed resource and optional tenant binding.
3. Action Model — closed action vocabulary: read/create/update/delete/approve/reject/execute/archive.
4. Resource Type Model — organization/project/decision/option/scenario/risk/execution/knowledge.
5. Authorization Context — immutable boundary combining security identity, actor, tenant, permission, resource, correlation ID and safe attributes.
6. Identity/Actor Consistency — authorization context rejects mismatched user/authentication identities.
7. Tenant Context Consistency — context tenant must match resource tenant.
8. Policy Contract — protocol for deterministic policy evaluation.
9. Policy Decision — immutable allow/deny result with reason, policy ID, permission and correlation ID.
10. Default-Deny Foundation — absence of an allow policy yields deterministic deny.
11. Explicit Permission Foundation Policy — foundation-only explicit grant evaluator.
12. Authorization Service — evaluates policies and exposes `require()` for fail-closed enforcement.
13. Application Port — stable evaluator contract for later API/application integration.
14. Tests — model, boundary, normalization, deterministic deny and authentication-boundary coverage.
15. Definition of Done — executable checks and release documentation.

## Security boundaries
- Authorization is fail-closed by default.
- Authentication identity is distinct from authorization permission.
- Roles are intentionally not implemented here.
- Tenant isolation policy is intentionally not implemented here.
- No AI or agent receives sovereign authorization authority from this stage.
- Authorization decisions are deterministic and explainable.
