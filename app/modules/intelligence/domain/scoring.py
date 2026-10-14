from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ScoreFactor:
    name: str
    value: float
    weight: float

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("score factor name is required")

        value = float(self.value)
        weight = float(self.weight)

        if not 0.0 <= value <= 1.0:
            raise ValueError("score factor value must be between 0 and 1")

        if weight < 0.0:
            raise ValueError("score factor weight cannot be negative")


@dataclass(frozen=True, slots=True)
class DeterministicScore:
    value: float
    factors: tuple[ScoreFactor, ...]

    def __post_init__(self) -> None:
        value = float(self.value)

        if not 0.0 <= value <= 1.0:
            raise ValueError("score must be between 0 and 1")

        if not isinstance(self.factors, tuple):
            raise ValueError("factors must be immutable tuple")

        if not self.factors:
            raise ValueError("at least one score factor is required")

        if not all(isinstance(item, ScoreFactor) for item in self.factors):
            raise ValueError("factors must contain ScoreFactor items")


class DeterministicScoringEngine:
    """Reproducible scoring; no AI/model dependency."""

    def calculate(self, factors: tuple[ScoreFactor, ...]) -> DeterministicScore:
        if not isinstance(factors, tuple):
            raise ValueError("factors must be immutable tuple")

        if not factors:
            raise ValueError("at least one score factor is required")

        total_weight = sum(item.weight for item in factors)

        if total_weight <= 0.0:
            raise ValueError("total score weight must be greater than zero")

        value = sum(
            item.value * item.weight
            for item in factors
        ) / total_weight

        return DeterministicScore(
            value=value,
            factors=factors,
        )
