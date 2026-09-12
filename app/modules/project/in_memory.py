from uuid import UUID
from app.modules.project.domain.models import Project
from app.modules.project.domain.repository import ProjectRepository


class InMemoryProjectRepository(ProjectRepository):
    def __init__(self):
        self._items: dict[UUID, Project] = {}

    def get_by_id(self, project_id):
        return self._items.get(project_id)

    def list_by_organization(self, organization_id):
        return [p for p in self._items.values() if p.organization_id == organization_id]

    def exists_by_name(self, organization_id, name):
        normalized = name.strip() if isinstance(name, str) else name
        return any(p.organization_id == organization_id and p.name == normalized for p in self._items.values())

    def save(self, project):
        self._items[project.id] = project
        return project


class DefaultProjectFactory:
    def create(self, organization_id, name, actor_id=None):
        return Project.create(organization_id, name, actor_id)
