from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from app.modules.authorization.domain.models import Resource, ResourceType
from app.modules.authorization.domain.resource_authorization import (
    ResourceRecord,
    ResourceStatus,
)
from app.modules.organization.application.tenant_resolver import (
    TenantOrganizationResolver,
)


@dataclass(frozen=True, slots=True)
class DeveloperResourceResolver:
    """
    Resolves protected developer resources to their persisted tenant.

    Tenant ownership is never inferred from resource IDs or organization IDs.
    Missing ownership and inconsistent relationships fail closed.
    """

    organization_repository: object
    project_repository: object
    decision_repository: object
    risk_repository: object
    _organization_tenant: TenantOrganizationResolver = field(init=False, repr=False)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "_organization_tenant",
            TenantOrganizationResolver(self.organization_repository),
        )

    @staticmethod
    def _resource_status(resource: object) -> ResourceStatus:
        value = getattr(getattr(resource, "status", None), "value", None)

        if value == ResourceStatus.ARCHIVED.value:
            return ResourceStatus.ARCHIVED

        if value == ResourceStatus.SUSPENDED.value:
            return ResourceStatus.SUSPENDED

        return ResourceStatus.ACTIVE

    def _tenant_for_organization(
        self,
        tenant_id: UUID,
        organization_id: UUID,
    ) -> bool:
        try:
            return self._organization_tenant.require(
                tenant_id=tenant_id,
                organization_id=organization_id,
            )
        except Exception:
            return False

    def _project(self, resource: Resource) -> ResourceRecord | None:
        project = self.project_repository.get_by_id(resource.resource_id)

        if project is None:
            return None

        tenant_id = resource.tenant_id
        if tenant_id is None:
            return None

        organization_id = project.organization_id

        if not self._tenant_for_organization(
            tenant_id,
            organization_id,
        ):
            return None

        resolved_resource = Resource(
            resource_type=ResourceType.PROJECT,
            resource_id=project.id,
            tenant_id=tenant_id,
            owner_id=None,
        )

        return ResourceRecord(
            resource=resolved_resource,
            owner_id=None,
            status=self._resource_status(project),
            exists=True,
        )

    def _decision(self, resource: Resource) -> ResourceRecord | None:
        decision = self.decision_repository.get_by_id(resource.resource_id)

        if decision is None:
            return None

        tenant_id = resource.tenant_id
        if tenant_id is None:
            return None

        organization_id = decision.organization_id

        # A Decision must reference a Project belonging to the same
        # organization. This prevents inconsistent cross-organization
        # relationships from becoming authorization paths.
        project = self.project_repository.get_by_id(
            decision.project_id,
            organization_id,
        )

        if project is None:
            return None

        if project.organization_id != organization_id:
            return None

        if not self._tenant_for_organization(
            tenant_id,
            organization_id,
        ):
            return None

        resolved_resource = Resource(
            resource_type=ResourceType.DECISION,
            resource_id=decision.id,
            tenant_id=tenant_id,
            owner_id=None,
        )

        return ResourceRecord(
            resource=resolved_resource,
            owner_id=None,
            status=self._resource_status(decision),
            exists=True,
        )

    def _risk(self, resource: Resource) -> ResourceRecord | None:
        risk = self.risk_repository.get_by_id(resource.resource_id)

        if risk is None:
            return None

        tenant_id = resource.tenant_id
        if tenant_id is None:
            return None

        project = self.project_repository.get_by_id(risk.project_id)

        if project is None:
            return None

        organization_id = project.organization_id

        if not self._tenant_for_organization(
            tenant_id,
            organization_id,
        ):
            return None

        resolved_resource = Resource(
            resource_type=ResourceType.RISK,
            resource_id=risk.id,
            tenant_id=tenant_id,
            owner_id=None,
        )

        return ResourceRecord(
            resource=resolved_resource,
            owner_id=None,
            status=self._resource_status(risk),
            exists=True,
        )

    def resolve(self, resource: Resource) -> ResourceRecord | None:
        if not isinstance(resource, Resource):
            return None

        try:
            resource_type = ResourceType(resource.resource_type)
        except (ValueError, TypeError):
            return None

        if resource_type is ResourceType.PROJECT:
            return self._project(resource)

        if resource_type is ResourceType.DECISION:
            return self._decision(resource)

        if resource_type is ResourceType.RISK:
            return self._risk(resource)

        # Developer resource authorization is deliberately limited to
        # resources with an explicitly implemented ownership chain.
        return None
