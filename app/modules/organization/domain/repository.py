from abc import ABC, abstractmethod
from uuid import UUID
from .models import Organization


class OrganizationRepository(ABC):
    @abstractmethod
    def get_by_id(self, organization_id: UUID) -> Organization | None: ...

    @abstractmethod
    def get_by_slug(self, slug: str) -> Organization | None: ...

    @abstractmethod
    def exists_by_slug(self, slug: str) -> bool: ...

    @abstractmethod
    def save(self, organization: Organization) -> Organization: ...
