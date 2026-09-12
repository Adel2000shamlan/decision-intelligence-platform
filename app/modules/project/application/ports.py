from dataclasses import dataclass
from typing import Protocol
from app.modules.project.domain.models import Project
from app.modules.project.domain.repository import ProjectRepository
from app.modules.organization.domain.repository import OrganizationRepository
from app.modules.project.domain.services import ProjectPolicyService


class ProjectFactory(Protocol):
    def create(self, organization_id, name: str, actor_id=None) -> Project: ...


@dataclass
class ProjectUnitOfWork:
    repository: ProjectRepository
    organization_repository: OrganizationRepository
    factory: ProjectFactory
    policy: ProjectPolicyService
    commit: callable
