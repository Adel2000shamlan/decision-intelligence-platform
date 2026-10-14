from __future__ import annotations

from uuid import UUID

from app.modules.learning.domain.models import (
    LearningObservation,
    LearningOutcomeType,
)
from app.modules.learning.persistence.repository import LearningRepository


class LearningService:
    """Application service for recording and querying observed decision outcomes."""

    def __init__(self, repository: LearningRepository):
        self.repository = repository

    def observe(
        self,
        *,
        tenant_id: UUID,
        decision_id: UUID,
        outcome_type: LearningOutcomeType,
        metric: str,
        source: str,
        expected_value: float | None = None,
        actual_value: float | None = None,
        notes: str | None = None,
        observed_at=None,
        confidence: float | None = None,
        source_event_id: UUID | None = None,
    ) -> LearningObservation:
        if source_event_id is not None:
            finder = getattr(self.repository, "get_by_source_event_id", None)
            if finder is not None:
                existing = finder(tenant_id, source_event_id)
                if existing is not None:
                    return existing

        observation = LearningObservation.create(
            tenant_id=tenant_id,
            decision_id=decision_id,
            outcome_type=outcome_type,
            expected_value=expected_value,
            actual_value=actual_value,
            metric=metric,
            source=source,
            notes=notes,
            observed_at=observed_at,
            confidence=confidence,
            source_event_id=source_event_id,
        )
        self.repository.save(observation)
        return observation

    def get(
        self,
        *,
        tenant_id: UUID,
        observation_id: UUID,
    ) -> LearningObservation | None:
        return self.repository.get(tenant_id, observation_id)

    def list(
        self,
        *,
        tenant_id: UUID,
        decision_id: UUID | None = None,
        metric: str | None = None,
    ) -> tuple[LearningObservation, ...]:
        return self.repository.list(
            tenant_id,
            decision_id=decision_id,
            metric=metric,
        )

    def remove(
        self,
        *,
        tenant_id: UUID,
        observation_id: UUID,
    ) -> None:
        self.repository.delete(tenant_id, observation_id)


# V113.05 - Learning Feedback
from app.modules.learning.domain.feedback import LearningFeedback


class LearningFeedbackService:
    """Builds tenant-scoped historical learning feedback."""

    def __init__(self, repository: LearningRepository) -> None:
        self.repository = repository

    def build(
        self,
        tenant_id: UUID,
        *,
        metric: str,
    ) -> LearningFeedback:
        if not isinstance(tenant_id, UUID):
            raise ValueError("tenant_id must be UUID")

        if not isinstance(metric, str) or not metric.strip():
            raise ValueError("metric is required")

        observations = self.repository.list(
            tenant_id,
            metric=metric.strip(),
        )

        return LearningFeedback.from_observations(
            tenant_id=tenant_id,
            metric=metric.strip(),
            observations=observations,
        )
