from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from .models import LearningObservation, LearningOutcomeType


@dataclass(frozen=True, slots=True)
class LearningFeedback:
    tenant_id: UUID
    metric: str
    observation_count: int
    success_count: int
    partial_count: int
    failure_count: int
    unknown_count: int
    average_variance: float | None
    average_confidence: float | None
    latest_observed_at: datetime | None
    observations: tuple[LearningObservation, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.tenant_id, UUID):
            raise ValueError("tenant_id must be UUID")
        if not isinstance(self.metric, str) or not self.metric.strip():
            raise ValueError("metric is required")
        if self.observation_count < 0:
            raise ValueError("observation_count cannot be negative")

        counts = (
            self.success_count,
            self.partial_count,
            self.failure_count,
            self.unknown_count,
        )
        if any(value < 0 for value in counts):
            raise ValueError("outcome counts cannot be negative")

        if sum(counts) != self.observation_count:
            raise ValueError("outcome counts must equal observation_count")

        if not isinstance(self.observations, tuple):
            raise ValueError("observations must be immutable tuple")

        if len(self.observations) != self.observation_count:
            raise ValueError("observations must match observation_count")

        if not all(
            isinstance(item, LearningObservation)
            for item in self.observations
        ):
            raise ValueError("observations must contain LearningObservation items")

        if self.average_variance is not None:
            object.__setattr__(self, "average_variance", float(self.average_variance))

        if self.average_confidence is not None:
            confidence = float(self.average_confidence)
            if not 0.0 <= confidence <= 1.0:
                raise ValueError("average_confidence must be between 0 and 1")
            object.__setattr__(self, "average_confidence", confidence)

    @classmethod
    def from_observations(
        cls,
        *,
        tenant_id: UUID,
        metric: str,
        observations: tuple[LearningObservation, ...],
    ) -> "LearningFeedback":
        if not isinstance(observations, tuple):
            raise ValueError("observations must be immutable tuple")

        if any(item.tenant_id != tenant_id for item in observations):
            raise ValueError("all observations must belong to tenant")

        if any(item.metric != metric for item in observations):
            raise ValueError("all observations must match metric")

        success = sum(
            item.outcome_type is LearningOutcomeType.SUCCESS
            for item in observations
        )
        partial = sum(
            item.outcome_type is LearningOutcomeType.PARTIAL
            for item in observations
        )
        failure = sum(
            item.outcome_type is LearningOutcomeType.FAILURE
            for item in observations
        )
        unknown = sum(
            item.outcome_type is LearningOutcomeType.UNKNOWN
            for item in observations
        )

        variances = [
            item.variance
            for item in observations
            if item.variance is not None
        ]
        confidences = [
            item.confidence
            for item in observations
            if item.confidence is not None
        ]

        latest = (
            max(item.observed_at for item in observations)
            if observations
            else None
        )

        return cls(
            tenant_id=tenant_id,
            metric=metric.strip(),
            observation_count=len(observations),
            success_count=success,
            partial_count=partial,
            failure_count=failure,
            unknown_count=unknown,
            average_variance=(
                sum(variances) / len(variances)
                if variances
                else None
            ),
            average_confidence=(
                sum(confidences) / len(confidences)
                if confidences
                else None
            ),
            latest_observed_at=latest,
            observations=observations,
        )
