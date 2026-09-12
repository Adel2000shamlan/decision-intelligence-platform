from dataclasses import dataclass
from uuid import UUID
from app.shared.domain.errors import EntityNotFound, BusinessRuleViolation
from .ports import OrganizationUnitOfWork


@dataclass(frozen=True)
class CreateOrganization:
    name: str
    slug: str
    actor_id: UUID | None = None


@dataclass(frozen=True)
class SuspendOrganization:
    organization_id: UUID
    actor_id: UUID | None = None


@dataclass(frozen=True)
class ReactivateOrganization:
    organization_id: UUID
    actor_id: UUID | None = None


@dataclass(frozen=True)
class ArchiveOrganization:
    organization_id: UUID
    actor_id: UUID | None = None


@dataclass(frozen=True)
class RenameOrganization:
    organization_id: UUID
    new_name: str
    actor_id: UUID | None = None


@dataclass(frozen=True)
class ChangeOrganizationSlug:
    organization_id: UUID
    new_slug: str
    actor_id: UUID | None = None


class OrganizationCommandHandler:
    def __init__(self, uow: OrganizationUnitOfWork):
        self.uow = uow

    def create(self, command: CreateOrganization):
        if self.uow.repository.exists_by_slug(command.slug):
            raise BusinessRuleViolation(f"organization slug already exists: {command.slug}")
        org = self.uow.repository.save(self.uow.factory.create(command.name, command.slug, command.actor_id))
        self.uow.commit()
        return org

    def _get(self, organization_id: UUID):
        org = self.uow.repository.get_by_id(organization_id)
        if org is None:
            raise EntityNotFound(f"organization not found: {organization_id}")
        return org

    def suspend(self, command: SuspendOrganization):
        org = self._get(command.organization_id); org.suspend(command.actor_id); self.uow.repository.save(org); self.uow.commit(); return org

    def reactivate(self, command: ReactivateOrganization):
        org = self._get(command.organization_id); org.reactivate(command.actor_id); self.uow.repository.save(org); self.uow.commit(); return org

    def archive(self, command: ArchiveOrganization):
        org = self._get(command.organization_id); org.archive(command.actor_id); self.uow.repository.save(org); self.uow.commit(); return org

    def rename(self, command: RenameOrganization):
        org = self._get(command.organization_id); org.rename(command.new_name, command.actor_id); self.uow.repository.save(org); self.uow.commit(); return org

    def change_slug(self, command: ChangeOrganizationSlug):
        if self.uow.repository.exists_by_slug(command.new_slug):
            existing = self.uow.repository.get_by_slug(command.new_slug)
            if existing and existing.id != command.organization_id:
                raise BusinessRuleViolation(f"organization slug already exists: {command.new_slug}")
        org = self._get(command.organization_id); org.change_slug(command.new_slug, command.actor_id); self.uow.repository.save(org); self.uow.commit(); return org
