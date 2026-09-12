from dataclasses import dataclass
from uuid import UUID
from app.shared.domain.errors import EntityNotFound
from app.modules.project.domain.models import Project, ProjectStatus
from app.modules.project.domain.services import ProjectDomainService

@dataclass(frozen=True)
class CreateProject: organization_id: UUID; name: str; actor_id: UUID|None=None; tenant_id: UUID|None=None
@dataclass(frozen=True)
class RenameProject: project_id: UUID; new_name: str; actor_id: UUID|None=None; tenant_id: UUID|None=None; expected_version: int|None=None
@dataclass(frozen=True)
class ActivateProject: project_id: UUID; actor_id: UUID|None=None
@dataclass(frozen=True)
class CompleteProject: project_id: UUID; actor_id: UUID|None=None
@dataclass(frozen=True)
class ArchiveProject: project_id: UUID; actor_id: UUID|None=None
@dataclass(frozen=True)
class CancelProject: project_id: UUID; actor_id: UUID|None=None
@dataclass(frozen=True)
class TransitionProject: project_id: UUID; status: ProjectStatus; actor_id: UUID|None=None; tenant_id: UUID|None=None; expected_version: int|None=None

class ProjectCommandHandler:
    def __init__(self, repository, organization_repository=None, tenant_guard=None, events=None, audit=None):
        if hasattr(repository, 'repository') and hasattr(repository, 'commit'):
            uow = repository
            repository = uow.repository
            organization_repository = uow.organization_repository
            self._commit = uow.commit
        else:
            self._commit = lambda: None
        self.repository=repository; self.organization_repository=organization_repository; self.tenant_guard=tenant_guard; self.events=events; self.audit=audit; self.domain=ProjectDomainService()
    def _save(self,p,expected):
        try: return self.repository.save(p,expected)
        except TypeError: return self.repository.save(p)
    def _access(self,p,tenant):
        if self.tenant_guard: self.tenant_guard.assert_access(p,tenant)
    def create(self,c):
        if self.organization_repository is not None:
            org=self.organization_repository.get_by_id(c.organization_id)
            if org is None: raise EntityNotFound(f'organization not found: {c.organization_id}')
            self.domain.ensure_organization_can_host(org)
        p=Project.create(c.organization_id,c.name,c.actor_id); self.domain.ensure_unique_name(self.repository,p); self._save(p, 0); self._commit(); self._post(p,c.actor_id,'create'); return p
    def _get(self,project_id,tenant=None):
        try: p=self.repository.get_by_id(project_id,tenant)
        except TypeError: p=self.repository.get_by_id(project_id)
        if p is None: raise EntityNotFound(f'project not found: {project_id}')
        if tenant is not None: self._access(p,tenant)
        return p
    def rename(self,c):
        p=self._get(c.project_id,c.tenant_id); old=p.version; p.rename(c.new_name,c.actor_id); self._save(p,c.expected_version if c.expected_version is not None else old); self._commit(); self._post(p,c.actor_id,'rename'); return p
    def archive(self, command): return self.transition(TransitionProject(command.project_id, ProjectStatus.ARCHIVED, command.actor_id, getattr(command,'tenant_id',None), getattr(command,'expected_version',None)))
    def cancel(self, command): return self.transition(TransitionProject(command.project_id, ProjectStatus.CANCELLED, command.actor_id, getattr(command,'tenant_id',None), getattr(command,'expected_version',None)))
    def activate(self, command): return self.transition(TransitionProject(command.project_id, ProjectStatus.ACTIVE, command.actor_id, getattr(command,'tenant_id',None), getattr(command,'expected_version',None)))
    def complete(self, command): return self.transition(TransitionProject(command.project_id, ProjectStatus.COMPLETED, command.actor_id, getattr(command,'tenant_id',None), getattr(command,'expected_version',None)))
    def transition(self,c):
        p=self._get(c.project_id,c.tenant_id); old=p.version; p.transition(c.status,c.actor_id); self._save(p,c.expected_version if c.expected_version is not None else old); self._commit(); self._post(p,c.actor_id,c.status.value); return p
    def _post(self,p,actor,action):
        if self.events:
            for e in p.pull_events(): self.events.publish(e)
        else: p.pull_events()
        if self.audit: self.audit.record(p.id,actor,action,p.version)
