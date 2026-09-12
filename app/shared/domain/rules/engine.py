from __future__ import annotations
from dataclasses import dataclass
from typing import Generic, Protocol, TypeVar
from app.shared.domain.errors import BusinessRuleViolation

T = TypeVar("T")

@dataclass(frozen=True)
class RuleContext:
    actor_id: object | None = None
    operation: str | None = None
    metadata: dict[str, object] | None = None

@dataclass(frozen=True)
class RuleResult:
    code: str
    message: str
    passed: bool = True

class DomainRule(Protocol, Generic[T]):
    code: str
    def check(self, target: T, context: RuleContext) -> RuleResult: ...

@dataclass(frozen=True)
class RuleEvaluation:
    results: tuple[RuleResult, ...]
    @property
    def passed(self) -> bool:
        return all(r.passed for r in self.results)
    @property
    def failures(self) -> tuple[RuleResult, ...]:
        return tuple(r for r in self.results if not r.passed)

class RuleSet(Generic[T]):
    """Deterministic, side-effect-free domain rule evaluator."""
    def __init__(self, rules: tuple[DomainRule[T], ...] = ()):
        self._rules = rules

    @property
    def rules(self) -> tuple[DomainRule[T], ...]:
        return self._rules

    def evaluate(self, target: T, context: RuleContext | None = None) -> RuleEvaluation:
        ctx = context or RuleContext()
        return RuleEvaluation(tuple(rule.check(target, ctx) for rule in self._rules))

    def assert_valid(self, target: T, context: RuleContext | None = None) -> None:
        evaluation = self.evaluate(target, context)
        if not evaluation.passed:
            first = evaluation.failures[0]
            raise BusinessRuleViolation(f"[{first.code}] {first.message}")

    def add(self, *rules: DomainRule[T]) -> "RuleSet[T]":
        return RuleSet(self._rules + tuple(rules))
