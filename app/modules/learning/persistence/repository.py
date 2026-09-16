from abc import ABC, abstractmethod
from uuid import UUID

from ..domain.models import LearningObservation


class LearningRepository(ABC):
    @abstractmethod
    def save(self, item: LearningObservation) -> LearningObservation:
        raise NotImplementedError

    @abstractmethod
    def get(
        self,
        tenant_id: UUID,
        observation_id: UUID,
    ) -> LearningObservation | None:
        raise NotImplementedError

    @abstractmethod
    def list(
        self,
        tenant_id: UUID,
        *,
        decision_id: UUID | None = None,
        metric: str | None = None,
    ) -> tuple[LearningObservation, ...]:
        raise NotImplementedError

    @abstractmethod
    def delete(self, tenant_id: UUID, observation_id: UUID) -> None:
        raise NotImplementedError
