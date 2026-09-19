from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID, uuid4

from app.modules.authorization.domain.models import (
    Action,
    AuthorizationContext,
    ExplicitPermissionPolicy,
    PolicyDecision,
    Permission,
    Resource,
    ResourceType,
)
from app.modules.authorization.domain.authorization_services import (
    AuthorizationServices,
    build_authorization_services,
)
from app.modules.authorization.domain.resource_authorization import ResourceResolver
from app.modules.developer.domain.models import (
    APIScope,
    DeveloperCredential,
    DeveloperCredentialStatus,
)
from app.modules.developer.security.credentials import (
    DeveloperCredentialSecurityService,
)
from app.modules.identity.domain.security_identity import (
    ActorContext,
    SecurityIdentity,
)


class DeveloperAuthorizationError(PermissionError):
    """Developer API authorization failure."""


@dataclass(frozen=True, slots=True)
class DeveloperScope:
    resource: ResourceType
    read_scope: APIScope
    write_scope: APIScope


_SCOPE_MATRIX: dict[ResourceType, DeveloperScope] = {
    ResourceType.PROJECT: DeveloperScope(
        ResourceType.PROJECT,
        APIScope.PROJECTS_READ,
        APIScope.PROJECTS_WRITE,
    ),
    ResourceType.DECISION: DeveloperScope(
        ResourceType.DECISION,
        APIScope.DECISIONS_READ,
        APIScope.DECISIONS_WRITE,
    ),
    ResourceType.RISK: DeveloperScope(
        ResourceType.RISK,
        APIScope.RISKS_READ,
        APIScope.RISKS_WRITE,
    ),
}


_READ_ACTIONS = frozenset({Action.READ})
_WRITE_ACTIONS = frozenset({
    Action.CREATE,
    Action.UPDATE,
    Action.DELETE,
})


@dataclass(frozen=True, slots=True)
class DeveloperAuthorizationService:
    credential_security: DeveloperCredentialSecurityService
    authorization: AuthorizationServices
    resource_resolver: ResourceResolver | None = None

    @classmethod
    def create(
        cls,
        credential_security: DeveloperCredentialSecurityService | None = None,
        authorization: AuthorizationServices | None = None,
        resource_resolver: ResourceResolver | None = None,
        policies: tuple[ExplicitPermissionPolicy, ...] = (),
    ) -> "DeveloperAuthorizationService":
        if authorization is not None and resource_resolver is not None:
            raise ValueError(
                "provide either authorization or resource_resolver, not both"
            )

        resolved_authorization = authorization
        if resolved_authorization is None:
            resolved_authorization = build_authorization_services(
                policies=policies,
                resource_resolver=resource_resolver,
            )

        return cls(
            credential_security=credential_security
            or DeveloperCredentialSecurityService(),
            authorization=resolved_authorization,
            resource_resolver=resource_resolver,
        )

    @staticmethod
    def required_scope(
        resource: ResourceType,
        action: Action,
    ) -> APIScope:
        try:
            mapping = _SCOPE_MATRIX[ResourceType(resource)]
        except (KeyError, ValueError, TypeError) as exc:
            raise DeveloperAuthorizationError(
                "unsupported developer API resource"
            ) from exc

        if action in _READ_ACTIONS:
            return mapping.read_scope

        if action in _WRITE_ACTIONS:
            return mapping.write_scope

        # Sensitive actions are intentionally not granted by a generic
        # developer write scope.
        raise DeveloperAuthorizationError(
            "developer credential does not grant this sensitive action"
        )

    def require(
        self,
        *,
        credential: DeveloperCredential,
        secret: str,
        user_id: UUID,
        authentication_id: UUID,
        tenant_id: UUID,
        resource: Resource,
        action: Action,
        assurance_level: str = "standard",
        actor_type: str = "human",
        now: datetime | None = None,
    ) -> PolicyDecision:
        if credential.tenant_id != tenant_id:
            raise DeveloperAuthorizationError("developer credential tenant mismatch")

        if credential.status is not DeveloperCredentialStatus.ACTIVE:
            raise DeveloperAuthorizationError("developer credential is not active")

        current = now or datetime.now(timezone.utc)
        if current.tzinfo is None:
            raise DeveloperAuthorizationError("now must be timezone-aware")

        if credential.is_expired(current):
            raise DeveloperAuthorizationError("developer credential is expired")

        if not self.credential_security.verify(
            credential,
            secret,
            now=current,
        ):
            raise DeveloperAuthorizationError("invalid developer credential")

        required = self.required_scope(resource.resource_type, action)

        if not credential.has_scope(required):
            raise DeveloperAuthorizationError(
                f"permission denied: missing scope {required.value}"
            )

        if resource.tenant_id != tenant_id:
            raise DeveloperAuthorizationError("resource tenant mismatch")

        identity = SecurityIdentity(
            user_id=user_id,
            authentication_id=authentication_id,
            assurance_level=assurance_level,
            authenticated=True,
        )

        actor = ActorContext(
            actor_id=user_id,
            authentication_id=authentication_id,
            correlation_id=uuid4(),
            actor_type=actor_type,
            authenticated=True,
        )

        context = AuthorizationContext(
            identity=identity,
            actor=actor,
            tenant_id=tenant_id,
            permission=Permission(
                resource.resource_type,
                action,
            ),
            resource=resource,
            correlation_id=actor.correlation_id,
        )

        decision = self.authorization.authorize(context)

        if not decision.allowed:
            raise DeveloperAuthorizationError(decision.reason)

        return decision
