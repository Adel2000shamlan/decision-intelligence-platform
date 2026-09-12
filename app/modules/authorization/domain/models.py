from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Protocol, Mapping
from uuid import UUID

from app.shared.domain.errors import InvalidDomainData, UnauthorizedDomainAction
from app.modules.identity.domain.security_identity import SecurityIdentity, ActorContext


class AuthorizationError(UnauthorizedDomainAction):
    """Base error for authorization-domain failures."""


class InvalidPermission(AuthorizationError): pass
class InvalidResource(AuthorizationError): pass
class InvalidAuthorizationContext(AuthorizationError): pass


class Action(str, Enum):
    READ = "read"
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    APPROVE = "approve"
    REJECT = "reject"
    EXECUTE = "execute"
    ARCHIVE = "archive"


class ResourceType(str, Enum):
    ORGANIZATION = "organization"
    PROJECT = "project"
    DECISION = "decision"
    OPTION = "option"
    SCENARIO = "scenario"
    RISK = "risk"
    EXECUTION = "execution"
    KNOWLEDGE = "knowledge"


@dataclass(frozen=True, slots=True)
class Permission:
    """Canonical authorization permission: resource_type:action."""
    resource: ResourceType
    action: Action

    def __post_init__(self) -> None:
        try:
            object.__setattr__(self, "resource", ResourceType(self.resource))
            object.__setattr__(self, "action", Action(self.action))
        except (ValueError, TypeError) as exc:
            raise InvalidPermission("invalid authorization permission") from exc

    @property
    def key(self) -> str:
        return f"{self.resource.value}:{self.action.value}"

    @classmethod
    def parse(cls, value: str) -> "Permission":
        if not isinstance(value, str) or value.count(":") != 1:
            raise InvalidPermission("permission must be resource:action")
        resource, action = value.strip().lower().split(":")
        if not resource or not action:
            raise InvalidPermission("permission must contain resource and action")
        return cls(ResourceType(resource), Action(action))


@dataclass(frozen=True, slots=True)
class Resource:
    """A resource protected by authorization and optionally bound to a tenant."""
    resource_type: ResourceType
    resource_id: UUID
    tenant_id: UUID | None = None
    owner_id: UUID | None = None

    def __post_init__(self) -> None:
        try:
            object.__setattr__(self, "resource_type", ResourceType(self.resource_type))
        except (ValueError, TypeError) as exc:
            raise InvalidResource("invalid resource type") from exc
        if not isinstance(self.resource_id, UUID):
            raise InvalidResource("resource_id must be UUID")
        if self.tenant_id is not None and not isinstance(self.tenant_id, UUID):
            raise InvalidResource("tenant_id must be UUID or None")
        if self.owner_id is not None and not isinstance(self.owner_id, UUID):
            raise InvalidResource("owner_id must be UUID or None")


@dataclass(frozen=True, slots=True)
class AuthorizationContext:
    """Complete input boundary for a single authorization decision."""
    identity: SecurityIdentity
    actor: ActorContext
    tenant_id: UUID | None
    permission: Permission
    resource: Resource
    correlation_id: UUID
    attributes: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.identity, SecurityIdentity):
            raise InvalidAuthorizationContext("identity is required")
        if not isinstance(self.actor, ActorContext):
            raise InvalidAuthorizationContext("actor context is required")
        if not isinstance(self.tenant_id, (UUID, type(None))):
            raise InvalidAuthorizationContext("tenant_id must be UUID or None")
        if not isinstance(self.permission, Permission):
            raise InvalidAuthorizationContext("permission is required")
        if not isinstance(self.resource, Resource):
            raise InvalidAuthorizationContext("resource is required")
        if not isinstance(self.correlation_id, UUID):
            raise InvalidAuthorizationContext("correlation_id must be UUID")
        if self.tenant_id != self.resource.tenant_id:
            raise InvalidAuthorizationContext("context tenant and resource tenant must match")
        if self.identity.user_id != self.actor.actor_id:
            raise InvalidAuthorizationContext("identity and actor user ids must match")
        if self.actor.authentication_id != self.identity.authentication_id:
            raise InvalidAuthorizationContext("identity and actor authentication ids must match")
        if not isinstance(self.attributes, tuple):
            raise InvalidAuthorizationContext("attributes must be immutable tuple pairs")
        for item in self.attributes:
            if not isinstance(item, tuple) or len(item) != 2 or not all(isinstance(x, str) for x in item):
                raise InvalidAuthorizationContext("attributes must contain string pairs")


@dataclass(frozen=True, slots=True)
class PolicyDecision:
    """Deterministic authorization result; deny is never implicit in allow."""
    allowed: bool
    reason: str
    policy_id: str
    permission: Permission
    correlation_id: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.allowed, bool):
            raise InvalidDomainData("allowed must be bool")
        if not isinstance(self.reason, str) or not self.reason.strip():
            raise InvalidDomainData("decision reason is required")
        if not isinstance(self.policy_id, str) or not self.policy_id.strip():
            raise InvalidDomainData("policy_id is required")
        if not isinstance(self.permission, Permission):
            raise InvalidDomainData("permission is required")
        if not isinstance(self.correlation_id, UUID):
            raise InvalidDomainData("correlation_id must be UUID")


class AuthorizationPolicy(Protocol):
    policy_id: str
    def evaluate(self, context: AuthorizationContext) -> PolicyDecision: ...


@dataclass(frozen=True, slots=True)
class ExplicitPermissionPolicy:
    """Foundation policy: allow only when an explicit permission key is present."""
    grants: frozenset[str] = frozenset()
    policy_id: str = "explicit-permission-v1"

    def __post_init__(self) -> None:
        normalized: set[str] = set()
        for grant in self.grants:
            normalized.add(Permission.parse(grant).key)
        object.__setattr__(self, "grants", frozenset(normalized))

    def evaluate(self, context: AuthorizationContext) -> PolicyDecision:
        allowed = context.permission.key in self.grants
        return PolicyDecision(
            allowed=allowed,
            reason="explicit permission granted" if allowed else "explicit permission not granted",
            policy_id=self.policy_id,
            permission=context.permission,
            correlation_id=context.correlation_id,
        )


@dataclass(frozen=True, slots=True)
class DefaultDenyPolicy:
    policy_id: str = "default-deny-v1"

    def evaluate(self, context: AuthorizationContext) -> PolicyDecision:
        return PolicyDecision(
            allowed=False,
            reason="authorization policy has no allow rule",
            policy_id=self.policy_id,
            permission=context.permission,
            correlation_id=context.correlation_id,
        )
