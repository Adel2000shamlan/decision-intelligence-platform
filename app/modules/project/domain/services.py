from __future__ import annotations
from uuid import UUID
from app.shared.domain.services import DomainServiceBase, ServiceResult
from app.shared.domain.errors import BusinessRuleViolation
from app.modules.organization.domain.models import Organization, OrganizationStatus
from .models import Project, ProjectStatus

class ProjectDomainService(DomainServiceBase):
    def create(self, project_repository, organization_repository, organization_id: UUID, name: str, actor_id: UUID | None = None) -> ServiceResult[Project]:
        organization = self.require(organization_repository.get_by_id(organization_id), 'organization', organization_id)
        self.ensure_organization_can_host(organization)
        project = Project.create(organization_id, name, actor_id)
        self.ensure_unique_name(project_repository, project)
        project_repository.save(project)
        return self.collect(project)

    def activate(self, repository, project_id: UUID, actor_id: UUID | None = None, expected_version: int | None = None) -> ServiceResult[Project]:
        return self._transition(repository, project_id, 'active', actor_id, expected_version)
    def complete(self, repository, project_id: UUID, actor_id: UUID | None = None, expected_version: int | None = None) -> ServiceResult[Project]:
        return self._transition(repository, project_id, 'completed', actor_id, expected_version)
    def cancel(self, repository, project_id: UUID, actor_id: UUID | None = None, expected_version: int | None = None) -> ServiceResult[Project]:
        return self._transition(repository, project_id, 'cancelled', actor_id, expected_version)
    def archive(self, repository, project_id: UUID, actor_id: UUID | None = None, expected_version: int | None = None) -> ServiceResult[Project]:
        return self._transition(repository, project_id, 'archived', actor_id, expected_version)

    def rename(self, repository, project_id: UUID, new_name: str, actor_id: UUID | None = None, expected_version: int | None = None) -> ServiceResult[Project]:
        project = self.require(repository.get_by_id(project_id), 'project', project_id)
        self.ensure_version(project, expected_version)
        if project.status.value == 'archived': raise BusinessRuleViolation('archived project cannot be renamed')
        if repository.exists_by_name(project.organization_id, new_name.strip()) and new_name.strip() != project.name:
            raise BusinessRuleViolation(f'project name already exists in organization: {new_name.strip()}')
        project.rename(new_name, actor_id); repository.save(project); return self.collect(project)

    @staticmethod
    def ensure_organization_can_host(organization: Organization) -> None:
        if organization.status is not OrganizationStatus.ACTIVE:
            raise BusinessRuleViolation('projects can only be hosted by an active organization')
    @staticmethod
    def ensure_unique_name(repository, project: Project) -> None:
        if repository.exists_by_name(project.organization_id, project.name):
            raise BusinessRuleViolation(f'project name already exists in organization: {project.name}')
    def _transition(self, repository, project_id, target, actor_id, expected_version):
        project = self.require(repository.get_by_id(project_id), 'project', project_id)
        self.ensure_version(project, expected_version)
        project.transition(ProjectStatus(target), actor_id); repository.save(project); return self.collect(project)

class ProjectPolicyService:
    def ensure_organization_can_host_project(self, organization: Organization) -> None:
        ProjectDomainService.ensure_organization_can_host(organization)
    def ensure_unique_name(self, repository, project: Project) -> None:
        ProjectDomainService.ensure_unique_name(repository, project)
