from abc import ABC, abstractmethod
from uuid import UUID

from ..domain.models import BenchmarkDefinition, BenchmarkObservation


class BenchmarkingRepository(ABC):
    """Persistence contract for tenant-scoped benchmark definitions and observations."""

    @abstractmethod
    def save_definition(
        self,
        definition: BenchmarkDefinition,
    ) -> BenchmarkDefinition:
        raise NotImplementedError

    @abstractmethod
    def get_definition(
        self,
        tenant_id: UUID,
        definition_id: UUID,
    ) -> BenchmarkDefinition | None:
        raise NotImplementedError

    @abstractmethod
    def list_definitions(
        self,
        tenant_id: UUID,
    ) -> tuple[BenchmarkDefinition, ...]:
        raise NotImplementedError

    @abstractmethod
    def delete_definition(
        self,
        tenant_id: UUID,
        definition_id: UUID,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    def save_observation(
        self,
        observation: BenchmarkObservation,
    ) -> BenchmarkObservation:
        raise NotImplementedError

    @abstractmethod
    def get_observation(
        self,
        tenant_id: UUID,
        observation_id: UUID,
    ) -> BenchmarkObservation | None:
        raise NotImplementedError

    @abstractmethod
    def list_observations(
        self,
        tenant_id: UUID,
        *,
        definition_id: UUID | None = None,
        peer_group: str | None = None,
        metric: str | None = None,
    ) -> tuple[BenchmarkObservation, ...]:
        raise NotImplementedError

    @abstractmethod
    def delete_observation(
        self,
        tenant_id: UUID,
        observation_id: UUID,
    ) -> None:
        raise NotImplementedError
