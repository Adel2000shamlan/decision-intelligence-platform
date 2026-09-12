# V104.05.05 — Action Authorization

Action authorization is a deterministic gate between mandatory authorization rules and resource/general policy evaluation.

## Ordered stages
1. Action policy contract.
2. Canonical action validation.
3. Sensitive-action actor boundary.
4. AI action boundary.
5. System action boundary.
6. Fail-closed evaluation.
7. AuthorizationPolicyEngine integration.
8. Trace integration.
9. Security and abuse tests.
10. Regression verification.
11. Definition of Done and release closure.

Sensitive actions (`approve`, `reject`, `execute`, `archive`, `delete`) require an authenticated human with strong assurance. AI actors cannot directly perform sensitive actions; system actors cannot directly approve/reject. These gates do not grant permission: explicit policy permission is still required later.
