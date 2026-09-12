from dataclasses import dataclass
from uuid import UUID
from app.shared.domain.errors import EntityNotFound

@dataclass
class ProjectQueryService:
    repository: object
    def get(self, project_id: UUID, tenant_id: UUID|None=None):
        p=self.repository.get_by_id(project_id,tenant_id)
        if p is None: raise EntityNotFound(f'project not found: {project_id}')
        return p
    def list(self, organization_id: UUID, tenant_id: UUID|None=None):
        if tenant_id is not None and organization_id != tenant_id: raise PermissionError('tenant boundary violation')
        return self.repository.list_by_organization(organization_id)
    def exists(self, organization_id: UUID, name: str): return self.repository.exists_by_name(organization_id,name)
