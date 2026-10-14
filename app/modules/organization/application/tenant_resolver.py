from __future__ import annotations

from uuid import UUID

from app.shared.domain.errors import BusinessRuleViolation


class TenantOrganizationResolver:
    """
    Resolves the persisted tenant ownership of an organization.

    This boundary intentionally never assumes:
        tenant_id == organization_id

    The organization repository is the source of truth for the
    tenant-to-organization relationship.
    """

    def __init__(self, repository) -> None:
        self.repository = repository

    def require(
        self,
        *,
        tenant_id: UUID,
        organization_id: UUID,
    ) -> bool:
        if not isinstance(tenant_id, UUID):
            raise BusinessRuleViolation("tenant_id must be a UUID")

        if not isinstance(organization_id, UUID):
            raise BusinessRuleViolation("organization_id must be a UUID")

        actual_tenant_id = self.repository.get_tenant_id(organization_id)

        if actual_tenant_id is None:
            raise BusinessRuleViolation(
                "organization tenant ownership is missing"
            )

        if actual_tenant_id != tenant_id:
            raise BusinessRuleViolation(
                "organization tenant mismatch"
            )

        return True
