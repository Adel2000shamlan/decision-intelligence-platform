from dataclasses import dataclass
from typing import Protocol
from .commands import *
from app.modules.organization.domain.models import Organization
from app.modules.organization.domain.repository import OrganizationRepository


class OrganizationFactory(Protocol):
    def create(self, name: str, slug: str, actor_id=None) -> Organization: ...


@dataclass
class OrganizationUnitOfWork:
    repository: OrganizationRepository
    factory: OrganizationFactory
    commit: callable
