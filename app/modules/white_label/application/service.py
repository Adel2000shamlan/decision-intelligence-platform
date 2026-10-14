from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from app.modules.authorization.domain.models import (
    Action,
    ActorContext,
    AuthorizationContext,
    Permission,
    Resource,
    ResourceType,
)
from app.modules.identity.domain.security_identity import SecurityIdentity
from app.modules.organization.application.tenant import OrganizationTenantGuard
from app.modules.organization.application.tenant_resolver import (
    TenantOrganizationResolver,
)
from app.modules.white_label.domain.models import (
    DEFAULT_BACKGROUND_COLOR,
    DEFAULT_DESCRIPTION,
    DEFAULT_DIRECTION,
    DEFAULT_DISPLAY_NAME,
    DEFAULT_LOCALE,
    DEFAULT_PRIMARY_COLOR,
    DEFAULT_SECONDARY_COLOR,
    DEFAULT_SHORT_NAME,
    DEFAULT_THEME_COLOR,
    WhiteLabelConfiguration,
)
from app.shared.domain.errors import (
    BusinessRuleViolation,
    EntityNotFound,
)


class WhiteLabelApplicationService:
    """
    Application boundary for tenant-scoped white-label configuration.

    Security invariant:
    configuration identity is never treated as proof of tenant ownership.
    Any configuration loaded by ID must be checked against the requested tenant.
    """

    def __init__(
        self,
        repository,
        organization_repository=None,
        authorization=None,
    ) -> None:
        self.repository = repository
        self.organization_repository = organization_repository
        self.authorization = authorization

        self.organization_guard = OrganizationTenantGuard()

        self.organization_resolver = (
            TenantOrganizationResolver(organization_repository)
            if organization_repository is not None
            else None
        )

    def _validate_tenant(self, tenant_id: UUID) -> None:
        if not isinstance(tenant_id, UUID):
            raise BusinessRuleViolation("tenant_id must be a UUID")

    def _authorize(
        self,
        *,
        action: str,
        actor_id,
        authentication_id,
        tenant_id: UUID,
        resource_id=None,
    ) -> None:
        if self.authorization is None:
            raise BusinessRuleViolation(
                "white-label authorization service is required"
            )

        if not isinstance(actor_id, UUID):
            raise BusinessRuleViolation("actor_id must be a UUID")

        if not isinstance(authentication_id, UUID):
            raise BusinessRuleViolation("authentication_id must be a UUID")

        action_value = Action(action)

        identity = SecurityIdentity(
            user_id=actor_id,
            authentication_id=authentication_id,
            assurance_level="standard",
            authenticated=True,
        )

        actor = ActorContext(
            actor_id=actor_id,
            authentication_id=authentication_id,
            correlation_id=uuid4(),
            actor_type="human",
            authenticated=True,
        )

        effective_resource_id = resource_id or tenant_id

        resource = Resource(
            resource_type=ResourceType.ORGANIZATION,
            resource_id=effective_resource_id,
            tenant_id=tenant_id,
        )

        context = AuthorizationContext(
            identity=identity,
            actor=actor,
            tenant_id=tenant_id,
            permission=Permission(
                ResourceType.ORGANIZATION,
                action_value,
            ),
            resource=resource,
            correlation_id=actor.correlation_id,
        )

        self.authorization.require(context)

    def _require_organization(
        self,
        *,
        tenant_id: UUID,
        organization_id: UUID,
    ):
        if self.organization_resolver is None:
            raise BusinessRuleViolation(
                "organization repository is required for organization-scoped white-label configuration"
            )

        organization = self.organization_repository.get_by_id(
            organization_id
        )

        if organization is None:
            raise EntityNotFound(
                f"organization not found: {organization_id}"
            )

        self.organization_resolver.require(
            tenant_id=tenant_id,
            organization_id=organization_id,
        )

        self.organization_guard.require(organization, tenant_id)

        return organization

    def get(
        self,
        *,
        tenant_id: UUID,
        actor_id=None,
        authentication_id=None,
    ) -> WhiteLabelConfiguration:
        """
        Return the tenant's white-label configuration.

        If no persisted configuration exists, return an ephemeral domain
        object containing platform defaults. Defaults are never persisted
        implicitly by a read operation.
        """
        self._validate_tenant(tenant_id)
        self._authorize(
            action="read",
            actor_id=actor_id,
            authentication_id=authentication_id,
            tenant_id=tenant_id,
        )

        configuration = self.repository.get_by_tenant(tenant_id)

        if configuration is None:
            return WhiteLabelConfiguration.create(
                tenant_id=tenant_id,
            )

        if configuration.tenant_id != tenant_id:
            raise BusinessRuleViolation(
                "white-label configuration tenant mismatch"
            )

        return configuration

    def _get_owned_configuration(
        self,
        *,
        tenant_id: UUID,
        configuration_id: UUID,
    ) -> WhiteLabelConfiguration:
        configuration = self.repository.get_by_id(configuration_id)

        if configuration is None:
            raise EntityNotFound(
                f"white-label configuration not found: {configuration_id}"
            )

        if configuration.tenant_id != tenant_id:
            raise BusinessRuleViolation(
                "white-label configuration tenant mismatch"
            )

        return configuration

    def get_by_id(
        self,
        *,
        tenant_id: UUID,
        configuration_id: UUID,
        actor_id=None,
        authentication_id=None,
    ) -> WhiteLabelConfiguration:
        """
        Resolve a configuration by ID only after enforcing tenant ownership.
        """
        self._validate_tenant(tenant_id)
        self._authorize(
            action="read",
            actor_id=actor_id,
            authentication_id=authentication_id,
            tenant_id=tenant_id,
            resource_id=configuration_id,
        )

        return self._get_owned_configuration(
            tenant_id=tenant_id,
            configuration_id=configuration_id,
        )

    def create(
        self,
        *,
        tenant_id: UUID,
        actor_id=None,
        authentication_id=None,
        organization_id: UUID | None = None,
        display_name: str = DEFAULT_DISPLAY_NAME,
        short_name: str = DEFAULT_SHORT_NAME,
        description: str = DEFAULT_DESCRIPTION,
        logo_url: str | None = None,
        favicon_url: str | None = None,
        primary_color: str = DEFAULT_PRIMARY_COLOR,
        secondary_color: str = DEFAULT_SECONDARY_COLOR,
        background_color: str = DEFAULT_BACKGROUND_COLOR,
        theme_color: str = DEFAULT_THEME_COLOR,
        locale: str = DEFAULT_LOCALE,
        direction: str = DEFAULT_DIRECTION,
    ) -> WhiteLabelConfiguration:
        self._validate_tenant(tenant_id)
        self._authorize(
            action="create",
            actor_id=actor_id,
            authentication_id=authentication_id,
            tenant_id=tenant_id,
        )

        if self.repository.get_by_tenant(tenant_id) is not None:
            raise BusinessRuleViolation(
                "white-label configuration already exists for tenant"
            )

        if organization_id is not None:
            self._require_organization(
                tenant_id=tenant_id,
                organization_id=organization_id,
            )

        configuration = WhiteLabelConfiguration.create(
            tenant_id=tenant_id,
            organization_id=organization_id,
            display_name=display_name,
            short_name=short_name,
            description=description,
            logo_url=logo_url,
            favicon_url=favicon_url,
            primary_color=primary_color,
            secondary_color=secondary_color,
            background_color=background_color,
            theme_color=theme_color,
            locale=locale,
            direction=direction,
        )

        return self.repository.save(configuration)

    def update(
        self,
        *,
        tenant_id: UUID,
        configuration_id: UUID,
        actor_id=None,
        authentication_id=None,
        organization_id: UUID | None = None,
        display_name: str = DEFAULT_DISPLAY_NAME,
        short_name: str = DEFAULT_SHORT_NAME,
        description: str = DEFAULT_DESCRIPTION,
        logo_url: str | None = None,
        favicon_url: str | None = None,
        primary_color: str = DEFAULT_PRIMARY_COLOR,
        secondary_color: str = DEFAULT_SECONDARY_COLOR,
        background_color: str = DEFAULT_BACKGROUND_COLOR,
        theme_color: str = DEFAULT_THEME_COLOR,
        locale: str = DEFAULT_LOCALE,
        direction: str = DEFAULT_DIRECTION,
    ) -> WhiteLabelConfiguration:
        self._validate_tenant(tenant_id)
        self._authorize(
            action="update",
            actor_id=actor_id,
            authentication_id=authentication_id,
            tenant_id=tenant_id,
            resource_id=configuration_id,
        )

        existing = self._get_owned_configuration(
            tenant_id=tenant_id,
            configuration_id=configuration_id,
        )

        if organization_id is not None:
            self._require_organization(
                tenant_id=tenant_id,
                organization_id=organization_id,
            )

        configuration = WhiteLabelConfiguration(
            id=existing.id,
            tenant_id=tenant_id,
            organization_id=organization_id,
            display_name=display_name,
            short_name=short_name,
            description=description,
            logo_url=logo_url,
            favicon_url=favicon_url,
            primary_color=primary_color,
            secondary_color=secondary_color,
            background_color=background_color,
            theme_color=theme_color,
            locale=locale,
            direction=direction,
            created_at=existing.created_at,
            updated_at=datetime.now(timezone.utc),
            version=existing.version + 1,
        )

        return self.repository.save(configuration)

    def delete(
        self,
        *,
        tenant_id: UUID,
        configuration_id: UUID,
        actor_id=None,
        authentication_id=None,
    ) -> None:
        self._validate_tenant(tenant_id)
        self._authorize(
            action="delete",
            actor_id=actor_id,
            authentication_id=authentication_id,
            tenant_id=tenant_id,
            resource_id=configuration_id,
        )

        self._get_owned_configuration(
            tenant_id=tenant_id,
            configuration_id=configuration_id,
        )

        self.repository.delete(configuration_id)
