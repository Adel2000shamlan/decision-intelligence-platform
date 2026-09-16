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
    ) -> LearningObservation:
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
