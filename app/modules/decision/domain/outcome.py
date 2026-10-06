from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from uuid import UUID


class DecisionOutcomeType(str, Enum):
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILURE = "failure"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class DecisionOutcome:
    outcome_type: DecisionOutcomeType
    metric: str
    expected_value: float | None = None
    actual_value: float | None = None
    notes: str | None = None
    confidence: float | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.outcome_type, DecisionOutcomeType):
            try:
                object.__setattr__(
                    self,
                    "outcome_type",
                    DecisionOutcomeType(self.outcome_type),
                )
            except (ValueError, TypeError) as exc:
                raise ValueError("invalid decision outcome type") from exc

        if not isinstance(self.metric, str) or not self.metric.strip():
            raise ValueError("metric is required")

        if self.expected_value is not None:
            if isinstance(self.expected_value, bool):
                raise ValueError("expected_value must be numeric")
            object.__setattr__(self, "expected_value", float(self.expected_value))

        if self.actual_value is not None:
            if isinstance(self.actual_value, bool):
                raise ValueError("actual_value must be numeric")
            object.__setattr__(self, "actual_value", float(self.actual_value))

        if self.notes is not None and not isinstance(self.notes, str):
            raise ValueError("notes must be a string")

        if self.confidence is not None:
            if isinstance(self.confidence, bool):
                raise ValueError("confidence must be numeric")
            confidence = float(self.confidence)
            if not 0.0 <= confidence <= 1.0:
                raise ValueError("confidence must be between 0 and 1")
            object.__setattr__(self, "confidence", confidence)
