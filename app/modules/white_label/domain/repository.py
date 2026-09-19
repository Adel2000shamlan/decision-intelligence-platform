from abc import ABC, abstractmethod
from uuid import UUID

from .models import WhiteLabelConfiguration


class WhiteLabelRepository(ABC):
    @abstractmethod
    def get_by_tenant(
        self,
        tenant_id: UUID,
    ) -> WhiteLabelConfiguration | None:
        ...

    @abstractmethod
    def get_by_id(
        self,
        configuration_id: UUID,
    ) -> WhiteLabelConfiguration | None:
        ...

    @abstractmethod
    def save(
        self,
        configuration: WhiteLabelConfiguration,
    ) -> WhiteLabelConfiguration:
        ...

    @abstractmethod
    def delete(self, configuration_id: UUID) -> None:
        ...
