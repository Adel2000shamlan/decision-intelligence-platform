from abc import ABC, abstractmethod
from uuid import UUID
from .models import Project


class ProjectRepository(ABC):
    @abstractmethod
    def get_by_id(self, project_id: UUID) -> Project | None: ...

    @abstractmethod
    def list_by_organization(self, organization_id: UUID) -> list[Project]: ...

    @abstractmethod
    def exists_by_name(self, organization_id: UUID, name: str) -> bool: ...

    @abstractmethod
    def save(self, project: Project) -> Project: ...
