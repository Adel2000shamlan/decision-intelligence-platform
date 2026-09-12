# V104.03.11 — Domain Rules

## Status
**IMPLEMENTED / VERIFIED / CLOSED**

## Scope
This stage establishes an explicit, deterministic domain-rule layer above aggregate invariants. Rules are side-effect free and return stable machine-readable rule codes before an application boundary converts a failed rule into `BusinessRuleViolation`.

## Implemented
- `app/shared/domain/rules/engine.py`
  - `RuleContext`
  - `RuleResult`
  - `RuleEvaluation`
  - `DomainRule` protocol
  - `RuleSet` evaluator/assertion API
- Organization rules
  - required/normalized name and slug constraints
  - valid lifecycle state
- Project rules
  - organization/name identity constraints
  - valid lifecycle state
- Risk rules
  - assessment completeness and deterministic score/level consistency
  - residual risk cannot exceed inherent risk
  - assessed-or-later states require an assessment
- Execution rules
  - progress and consumption bounds
  - completion requires 100% progress
  - schedule consistency
  - task/milestone progress bounds
- All four implemented aggregates now invoke their rule sets through `validate_invariants()`.

## Guarantees
1. Rules are deterministic and side-effect free.
2. Multiple failures can be collected by `evaluate()`.
3. `assert_valid()` reports the first failure with a stable rule code.
4. Existing constructor-level validation remains intact; the rule layer is an additional boundary guarantee, not a replacement.
5. Rules do not call repositories, AI providers, network services, clocks, or persistence.
6. Business policies that require another aggregate/repository remain in policy services rather than being hidden inside entity rules.

## Verification
- Full test suite: **89 passed**
- Python compile check: **OK**
- No infrastructure dependency introduced.

## Boundary note
The current V104.03.10 baseline contains integrated Organization, Project, Risk, and Execution aggregates. Decision, Option, and Scenario implementations are not falsely marked as present in this artifact; their rule sets should be attached when those modules are merged into the integrated baseline.
