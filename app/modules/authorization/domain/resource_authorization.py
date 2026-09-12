from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Protocol
from uuid import UUID

from .models import Action, AuthorizationContext, PolicyDecision, Resource, ResourceType


class ResourceAuthorizationError(Exception):
    pass


class ResourceStatus(str, Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    ARCHIVED = "archived"


@dataclass(frozen=True, slots=True)
class ResourceRecord:
    """Minimal authorization projection; never carries secrets or credentials."""
    resource: Resource
    owner_id: UUID | None = None
    status: ResourceStatus = ResourceStatus.ACTIVE
    exists: bool = True


class ResourceResolver(Protocol):
    def resolve(self, resource: Resource) -> ResourceRecord | None: ...


@dataclass(frozen=True, slots=True)
class InMemoryResourceResolver:
    records: tuple[ResourceRecord, ...] = ()

    def resolve(self, resource: Resource) -> ResourceRecord | None:
        for record in self.records:
            if record.resource == resource:
                return record
        return None


class ResourceAuthorizationPolicy(Protocol):
    policy_id: str
    def evaluate(self, context: AuthorizationContext, record: ResourceRecord) -> PolicyDecision: ...


@dataclass(frozen=True, slots=True)
class ResourceExistencePolicy:
    policy_id: str = "auth.resource.exists.v1"

    def evaluate(self, context: AuthorizationContext, record: ResourceRecord) -> PolicyDecision:
        allowed = record.exists and record.status is not ResourceStatus.ARCHIVED
        return PolicyDecision(
            allowed,
            "resource exists and is active" if allowed else "resource is unavailable",
            self.policy_id, context.permission, context.correlation_id,
        )


@dataclass(frozen=True, slots=True)
class ResourceTenantPolicy:
    policy_id: str = "auth.resource.tenant.v1"

    def evaluate(self, context: AuthorizationContext, record: ResourceRecord) -> PolicyDecision:
        allowed = record.resource.tenant_id == context.tenant_id
        return PolicyDecision(
            allowed,
            "resource belongs to authorization tenant" if allowed else "resource is outside authorization tenant",
            self.policy_id, context.permission, context.correlation_id,
        )


@dataclass(frozen=True, slots=True)
class ResourceOwnerPolicy:
    """Owner restriction is opt-in per resource projection; absence of owner is not ownership denial."""
    protected_actions: frozenset[Action] = frozenset({Action.UPDATE, Action.DELETE, Action.ARCHIVE, Action.APPROVE, Action.REJECT, Action.EXECUTE})
    policy_id: str = "auth.resource.owner.v1"

    def evaluate(self, context: AuthorizationContext, record: ResourceRecord) -> PolicyDecision:
        if context.permission.action not in self.protected_actions or record.owner_id is None:
            return PolicyDecision(True, "ownership restriction not applicable", self.policy_id, context.permission, context.correlation_id)
        allowed = record.owner_id == context.identity.user_id
        return PolicyDecision(
            allowed,
            "actor owns protected resource" if allowed else "actor does not own protected resource",
            self.policy_id, context.permission, context.correlation_id,
        )


@dataclass(frozen=True, slots=True)
class ResourceTypePolicy:
    policy_id: str = "auth.resource.type.v1"

    def evaluate(self, context: AuthorizationContext, record: ResourceRecord) -> PolicyDecision:
        allowed = context.permission.resource is record.resource.resource_type
        return PolicyDecision(
            allowed,
            "permission matches resource type" if allowed else "permission does not match resource type",
            self.policy_id, context.permission, context.correlation_id,
        )


DEFAULT_RESOURCE_POLICIES: tuple[ResourceAuthorizationPolicy, ...] = (
    ResourceExistencePolicy(),
    ResourceTenantPolicy(),
    ResourceTypePolicy(),
    ResourceOwnerPolicy(),
)


@dataclass(frozen=True, slots=True)
class ResourceAuthorizationEvaluation:
    decision: PolicyDecision
    policy_id: str
    sequence: int


@dataclass(frozen=True, slots=True)
class ResourceAuthorizationEngine:
    resolver: ResourceResolver
    policies: tuple[ResourceAuthorizationPolicy, ...] = DEFAULT_RESOURCE_POLICIES

    def evaluate(self, context: AuthorizationContext) -> PolicyDecision:
        record = self.resolver.resolve(context.resource)
        if record is None:
            return PolicyDecision(False, "protected resource was not found", "auth.resource.exists.v1", context.permission, context.correlation_id)
        for policy in self.policies:
            try:
                decision = policy.evaluate(context, record)
                if not isinstance(decision, PolicyDecision):
                    raise TypeError("resource authorization policy must return PolicyDecision")
            except Exception:
                return PolicyDecision(False, "resource authorization policy evaluation failed", getattr(policy, "policy_id", "unknown-resource-policy"), context.permission, context.correlation_id)
            if not decision.allowed:
                return decision
        return PolicyDecision(True, "resource authorization policies satisfied", "resource-authorization-v1", context.permission, context.correlation_id)
