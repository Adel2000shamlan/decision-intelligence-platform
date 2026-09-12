from dataclasses import dataclass
from uuid import UUID
from app.modules.project.domain.models import Project
from app.modules.project.persistence.sqlite import SQLiteProjectRepository

@dataclass
class ProjectRepositoryAdapter:
    backend: SQLiteProjectRepository
    def get_by_id(self, project_id: UUID, organization_id: UUID|None=None): return self.backend.get_by_id(project_id, organization_id)
    def list_by_organization(self, organization_id: UUID): return self.backend.list_by_organization(organization_id)
    def exists_by_name(self, organization_id: UUID, name: str): return self.backend.exists_by_name(organization_id, name)
    def save(self, project: Project, expected_version: int|None=None): return self.backend.save(project, expected_version)
