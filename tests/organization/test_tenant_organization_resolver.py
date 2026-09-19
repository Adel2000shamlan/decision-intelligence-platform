from uuid import uuid4

import pytest

from app.modules.organization.application.tenant_resolver import (
    TenantOrganizationResolver,
)
from app.modules.organization.persistence.sqlite import (
    SQLiteOrganizationRepository,
)
from app.modules.organization.domain.models import Organization
from app.shared.domain.errors import BusinessRuleViolation


def make_repository(tenant_id):
    repository = SQLiteOrganizationRepository()
    organization = Organization.create("Boundary Org", "boundary-org")
    repository.save(organization, tenant_id=tenant_id)
    return repository, organization


def test_same_tenant_allows():
    tenant_id = uuid4()
    repository, organization = make_repository(tenant_id)

    resolver = TenantOrganizationResolver(repository)

    assert resolver.require(
        tenant_id=tenant_id,
        organization_id=organization.id,
    ) is True


def test_different_tenant_rejects():
    owner_tenant_id = uuid4()
    other_tenant_id = uuid4()

    repository, organization = make_repository(owner_tenant_id)
    resolver = TenantOrganizationResolver(repository)

    with pytest.raises(BusinessRuleViolation, match="tenant mismatch"):
        resolver.require(
            tenant_id=other_tenant_id,
            organization_id=organization.id,
        )


def test_missing_organization_rejects_safely():
    tenant_id = uuid4()
    repository = SQLiteOrganizationRepository()
    resolver = TenantOrganizationResolver(repository)

    with pytest.raises(
        BusinessRuleViolation,
        match="tenant ownership is missing",
    ):
        resolver.require(
            tenant_id=tenant_id,
            organization_id=uuid4(),
        )


def test_organization_without_tenant_rejects_safely():
    repository = SQLiteOrganizationRepository()
    organization = Organization.create("Orphan Org", "orphan-org")
    repository.save(organization)

    resolver = TenantOrganizationResolver(repository)

    with pytest.raises(
        BusinessRuleViolation,
        match="tenant ownership is missing",
    ):
        resolver.require(
            tenant_id=uuid4(),
            organization_id=organization.id,
        )


def test_tenant_id_is_not_organization_id():
    tenant_id = uuid4()
    repository, organization = make_repository(tenant_id)

    assert tenant_id != organization.id

    resolver = TenantOrganizationResolver(repository)

    assert resolver.require(
        tenant_id=tenant_id,
        organization_id=organization.id,
    ) is True
