# V104.03.09 — Value Objects

## Objective
Establish immutable, validated domain primitives shared by Organization, Project, Decision, Option, Scenario, Risk, Execution, and future domains.

## Implemented value objects
- `Money`: Decimal arithmetic, 2-decimal quantization, currency normalization, same-currency arithmetic, no negative balances.
- `Probability`: decimal fraction `[0,1]` with percentage conversion.
- `Percentage`: human-facing `[0,100]` representation with fraction conversion.
- `Score`: bounded score with configurable bounds and health-score factory.
- `NonNegativeNumber`: finite non-negative quantity.
- `Identifier`: UUID boundary wrapper.
- `Name`: required normalized bounded name.
- `Description`: optional normalized bounded description.
- `Slug`: normalized lowercase URL-safe identifier.
- `EmailAddress`: normalized basic email value.
- `URL`: HTTP/HTTPS URL value.
- `DateRange`: inclusive date range with day count and containment.

## Design guarantees
1. Immutable dataclasses (`frozen=True`, `slots=True`).
2. Domain validation occurs at construction, not at API or persistence layers only.
3. Decimal is used for money and bounded numeric values where precision matters.
4. Boolean values are not accepted as numeric domain values.
5. NaN and infinity are rejected.
6. Money arithmetic cannot silently mix currencies.
7. Value objects have no database, HTTP, framework, or provider dependencies.
8. Existing `Probability(value: 0..1)` behavior is preserved for backward compatibility.
9. These objects are reusable across domains without coupling aggregates to infrastructure.

## Non-goals
- No ORM mapping.
- No API serialization policy.
- No provider-specific validation.
- No mutation of aggregate lifecycle rules.

## Verification
The complete project test suite must remain green, plus dedicated Value Object tests. Compilation is checked with `compileall`.
