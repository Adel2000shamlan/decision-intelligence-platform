from __future__ import annotations
from uuid import UUID
from app.shared.domain.services import DomainServiceBase, ServiceResult
from app.shared.domain.errors import BusinessRuleViolation
from .models import Organization

class OrganizationDomainService(DomainServiceBase):
    def create(self, repository, name: str, slug: str, actor_id: UUID | None = None) -> ServiceResult[Organization]:
        organization = Organization.create(name, slug, actor_id)
        self._ensure_unique_slug(repository, organization)
        repository.save(organization)
        return self.collect(organization)

    def suspend(self, repository, organization_id: UUID, actor_id: UUID | None = None, expected_version: int | None = None) -> ServiceResult[Organization]:
        organization = self.require(repository.get_by_id(organization_id), 'organization', organization_id)
        self.ensure_version(organization, expected_version)
        organization.suspend(actor_id); repository.save(organization); return self.collect(organization)

    def reactivate(self, repository, organization_id: UUID, actor_id: UUID | None = None, expected_version: int | None = None) -> ServiceResult[Organization]:
        organization = self.require(repository.get_by_id(organization_id), 'organization', organization_id)
        self.ensure_version(organization, expected_version)
        organization.reactivate(actor_id); repository.save(organization); return self.collect(organization)

    def archive(self, repository, organization_id: UUID, actor_id: UUID | None = None, expected_version: int | None = None) -> ServiceResult[Organization]:
        organization = self.require(repository.get_by_id(organization_id), 'organization', organization_id)
        self.ensure_version(organization, expected_version)
        organization.archive(actor_id); repository.save(organization); return self.collect(organization)

    def rename(self, repository, organization_id: UUID, new_name: str, actor_id: UUID | None = None, expected_version: int | None = None) -> ServiceResult[Organization]:
        organization = self.require(repository.get_by_id(organization_id), 'organization', organization_id)
        self.ensure_version(organization, expected_version)
        if organization.status.value == 'archived': raise BusinessRuleViolation('archived organization cannot be renamed')
        organization.rename(new_name, actor_id); repository.save(organization); return self.collect(organization)

    def change_slug(self, repository, organization_id: UUID, new_slug: str, actor_id: UUID | None = None, expected_version: int | None = None) -> ServiceResult[Organization]:
        organization = self.require(repository.get_by_id(organization_id), 'organization', organization_id)
        self.ensure_version(organization, expected_version)
        if organization.status.value == 'archived': raise BusinessRuleViolation('archived organization cannot change slug')
        organization.change_slug(new_slug, actor_id); self._ensure_unique_slug(repository, organization); repository.save(organization); return self.collect(organization)

    @staticmethod
    def _ensure_unique_slug(repository, organization: Organization) -> None:
        existing = repository.get_by_slug(organization.slug)
        if existing is not None and existing.id != organization.id:
            raise BusinessRuleViolation(f'organization slug already exists: {organization.slug}')

class OrganizationPolicyService:
    """Backward-compatible policy facade; orchestration lives in OrganizationDomainService."""
    def ensure_unique_slug(self, repository, organization: Organization) -> None:
        OrganizationDomainService._ensure_unique_slug(repository, organization)
