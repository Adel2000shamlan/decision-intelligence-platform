from abc import ABC, abstractmethod
from uuid import UUID

from ..domain.models import MemoryItem, MemoryStatus, MemoryType


class MemoryRepository(ABC):
    @abstractmethod
    def save(self, item: MemoryItem) -> MemoryItem:
        raise NotImplementedError

    @abstractmethod
    def get(self, tenant_id: UUID, memory_id: UUID) -> MemoryItem | None:
        raise NotImplementedError

    @abstractmethod
    def list(
        self,
        tenant_id: UUID,
        *,
        memory_type: MemoryType | None = None,
        status: MemoryStatus | None = None,
    ) -> tuple[MemoryItem, ...]:
        raise NotImplementedError

    @abstractmethod
    def delete(self, tenant_id: UUID, memory_id: UUID) -> None:
        raise NotImplementedError
