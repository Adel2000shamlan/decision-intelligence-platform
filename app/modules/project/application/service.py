from dataclasses import dataclass
from uuid import UUID
from app.modules.project.domain.models import ProjectStatus
from app.modules.project.application.commands import ProjectCommandHandler,CreateProject,RenameProject,TransitionProject
from app.modules.project.application.queries import ProjectQueryService
from app.modules.project.application.validation import ProjectApplicationValidator
@dataclass
class ProjectApplicationFacade:
    commands: ProjectCommandHandler
    queries: ProjectQueryService
    authorization: object|None=None
    def create(self,organization_id,name,actor_id=None,tenant_id=None):
        if self.authorization:self.authorization.require('create',actor_id,tenant_id)
        ProjectApplicationValidator.validate_create(organization_id,name)
        return self.commands.create(CreateProject(organization_id,name,actor_id,tenant_id))
    def get(self,project_id,tenant_id=None): return self.queries.get(project_id,tenant_id)
    def list(self,organization_id,tenant_id=None): return self.queries.list(organization_id,tenant_id)
    def rename(self,project_id,name,actor_id=None,tenant_id=None,expected_version=None):
        if self.authorization:self.authorization.require('update',actor_id,tenant_id,project_id)
        ProjectApplicationValidator.validate_expected_version(expected_version)
        return self.commands.rename(RenameProject(project_id,name,actor_id,tenant_id,expected_version))
    def transition(self,project_id,status,actor_id=None,tenant_id=None,expected_version=None):
        if self.authorization:self.authorization.require(status.value if isinstance(status,ProjectStatus) else str(status),actor_id,tenant_id,project_id)
        ProjectApplicationValidator.validate_transition(status); ProjectApplicationValidator.validate_expected_version(expected_version)
        return self.commands.transition(TransitionProject(project_id,ProjectStatus(status),actor_id,tenant_id,expected_version))


# Backward-compatible V104.07.01 service.
class ProjectApplicationService:
    def __init__(self, repository):
        self.repository=repository
    def create(self, organization_id, name, actor_id=None):
        from app.modules.project.domain.models import Project
        p=Project.create(organization_id,name,actor_id); self.repository.save(p); return p
    def get(self, project_id): return self.repository.get_by_id(project_id)
    def list(self, organization_id=None):
        return self.repository.list_by_organization(organization_id) if organization_id is not None else []
    def rename(self, project_id, name, actor_id=None):
        p=self.get(project_id)
        if p is None: raise LookupError(f'project not found: {project_id}')
        p.rename(name,actor_id); p.validate_invariants(); self.repository.save(p); return p
    def transition(self, project_id, status, actor_id=None):
        p=self.get(project_id)
        if p is None: raise LookupError(f'project not found: {project_id}')
        p.transition(status,actor_id); p.validate_invariants(); self.repository.save(p); return p
