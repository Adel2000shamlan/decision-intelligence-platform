from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from uuid import UUID, uuid4

from app.shared.domain.errors import BusinessRuleViolation


class LearningOutcomeType(str, Enum):
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILURE = "failure"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class LearningObservation:
    id: UUID
    tenant_id: UUID
    decision_id: UUID
    outcome_type: LearningOutcomeType
    expected_value: float | None
    actual_value: float | None
    metric: str
    source: str
    notes: str | None
    observed_at: datetime
    confidence: float | None
    created_at: datetime
    source_event_id: UUID | None = None

    @classmethod
    def create(
        cls,
        *,
        tenant_id: UUID,
        decision_id: UUID,
        outcome_type: LearningOutcomeType,
        metric: str,
        source: str,
        expected_value: float | None = None,
        actual_value: float | None = None,
        notes: str | None = None,
        observed_at: datetime | None = None,
        confidence: float | None = None,
        source_event_id: UUID | None = None,
    ) -> "LearningObservation":
        if not isinstance(tenant_id, UUID):
            raise BusinessRuleViolation("tenant_id must be a UUID")

        if not isinstance(decision_id, UUID):
            raise BusinessRuleViolation("decision_id must be a UUID")

        if source_event_id is not None and not isinstance(source_event_id, UUID):
            raise BusinessRuleViolation("source_event_id must be a UUID")

        if not isinstance(outcome_type, LearningOutcomeType):
            try:
                outcome_type = LearningOutcomeType(outcome_type)
            except (TypeError, ValueError) as exc:
                raise BusinessRuleViolation("invalid learning outcome type") from exc

        if not isinstance(metric, str) or not metric.strip():
            raise BusinessRuleViolation("metric must not be empty")

        if not isinstance(source, str) or not source.strip():
            raise BusinessRuleViolation("source must not be empty")

        for name, value in (
            ("expected_value", expected_value),
            ("actual_value", actual_value),
        ):
            if value is not None:
                if isinstance(value, bool) or not isinstance(value, (int, float)):
                    raise BusinessRuleViolation(f"{name} must be numeric")
                if value != value:
                    raise BusinessRuleViolation(f"{name} must not be NaN")

        if confidence is not None:
            if isinstance(confidence, bool) or not isinstance(
                confidence, (int, float)
            ):
                raise BusinessRuleViolation("confidence must be numeric")
            if not 0 <= confidence <= 1:
                raise BusinessRuleViolation("confidence must be between 0 and 1")

        observed = observed_at or datetime.now(timezone.utc)
        if observed.tzinfo is None:
            raise BusinessRuleViolation("observed_at must be timezone-aware")

        created = datetime.now(timezone.utc)

        return cls(
            id=uuid4(),
            tenant_id=tenant_id,
            decision_id=decision_id,
            outcome_type=outcome_type,
            expected_value=(
                float(expected_value) if expected_value is not None else None
            ),
            actual_value=float(actual_value) if actual_value is not None else None,
            metric=metric.strip(),
            source=source.strip(),
            notes=notes.strip() if isinstance(notes, str) and notes.strip() else None,
            observed_at=observed,
            confidence=float(confidence) if confidence is not None else None,
            created_at=created,
            source_event_id=source_event_id,
        )

    @property
    def variance(self) -> float | None:
        if self.expected_value is None or self.actual_value is None:
            return None
        return self.actual_value - self.expected_value
