from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Protocol

from app.shared.domain.errors import BusinessRuleViolation
from .models import Action, AuthorizationContext, ResourceType


class RuleEffect(str, Enum):
    ALLOW = "allow"
    DENY = "deny"


@dataclass(frozen=True, slots=True)
class RuleResult:
    effect: RuleEffect
    rule_id: str
    reason: str

    @property
    def allowed(self) -> bool:
        return self.effect is RuleEffect.ALLOW


class AuthorizationRule(Protocol):
    rule_id: str
    def evaluate(self, context: AuthorizationContext) -> RuleResult: ...


class AuthorizationRuleViolation(BusinessRuleViolation):
    """Raised when a mandatory authorization rule rejects an operation."""


@dataclass(frozen=True, slots=True)
class AuthenticatedActorRule:
    rule_id: str = "auth.actor.authenticated.v1"
    def evaluate(self, context: AuthorizationContext) -> RuleResult:
        if context.actor.authenticated and context.actor.actor_id is not None:
            return RuleResult(RuleEffect.ALLOW, self.rule_id, "actor is authenticated")
        return RuleResult(RuleEffect.DENY, self.rule_id, "authenticated actor is required")


@dataclass(frozen=True, slots=True)
class IdentityConsistencyRule:
    rule_id: str = "auth.identity.actor-consistency.v1"
    def evaluate(self, context: AuthorizationContext) -> RuleResult:
        if context.identity.user_id != context.actor.actor_id:
            return RuleResult(RuleEffect.DENY, self.rule_id, "identity and actor mismatch")
        if context.identity.authentication_id != context.actor.authentication_id:
            return RuleResult(RuleEffect.DENY, self.rule_id, "authentication identity mismatch")
        return RuleResult(RuleEffect.ALLOW, self.rule_id, "identity and actor are consistent")


@dataclass(frozen=True, slots=True)
class TenantBindingRule:
    rule_id: str = "auth.tenant.resource-binding.v1"
    def evaluate(self, context: AuthorizationContext) -> RuleResult:
        if context.tenant_id != context.resource.tenant_id:
            return RuleResult(RuleEffect.DENY, self.rule_id, "tenant context does not match resource")
        return RuleResult(RuleEffect.ALLOW, self.rule_id, "tenant binding is consistent")


@dataclass(frozen=True, slots=True)
class ExplicitPermissionRequirementRule:
    """No authorization rule may manufacture permission grants."""
    rule_id: str = "auth.permission.explicit.v1"
    def evaluate(self, context: AuthorizationContext) -> RuleResult:
        grants = dict(context.attributes).get("grants", "")
        grant_set = {x.strip().lower() for x in grants.split(",") if x.strip()}
        if context.permission.key in grant_set:
            return RuleResult(RuleEffect.ALLOW, self.rule_id, "explicit permission is present")
        return RuleResult(RuleEffect.DENY, self.rule_id, "explicit permission is required")


SENSITIVE_ACTIONS = frozenset({Action.APPROVE, Action.REJECT, Action.EXECUTE, Action.ARCHIVE, Action.DELETE})


@dataclass(frozen=True, slots=True)
class SensitiveActionRule:
    rule_id: str = "auth.sensitive-action.v1"
    def evaluate(self, context: AuthorizationContext) -> RuleResult:
        if context.permission.action not in SENSITIVE_ACTIONS:
            return RuleResult(RuleEffect.ALLOW, self.rule_id, "operation is not classified as sensitive")
        if context.actor.actor_type != "human":
            return RuleResult(RuleEffect.DENY, self.rule_id, "sensitive action requires a human actor")
        if not context.identity.authenticated:
            return RuleResult(RuleEffect.DENY, self.rule_id, "sensitive action requires authenticated identity")
        if context.identity.assurance_level != "strong":
            return RuleResult(RuleEffect.DENY, self.rule_id, "sensitive action requires strong authentication assurance")
        return RuleResult(RuleEffect.ALLOW, self.rule_id, "sensitive action satisfies human and assurance requirements")


@dataclass(frozen=True, slots=True)
class ResourceActionCompatibilityRule:
    rule_id: str = "auth.resource-action.compatibility.v1"
    def evaluate(self, context: AuthorizationContext) -> RuleResult:
        if context.permission.resource is not context.resource.resource_type:
            return RuleResult(RuleEffect.DENY, self.rule_id, "permission resource does not match protected resource")
        return RuleResult(RuleEffect.ALLOW, self.rule_id, "permission resource matches protected resource")


DEFAULT_AUTHORIZATION_RULES: tuple[AuthorizationRule, ...] = (
    AuthenticatedActorRule(),
    IdentityConsistencyRule(),
    TenantBindingRule(),
    ResourceActionCompatibilityRule(),
    SensitiveActionRule(),
)


def evaluate_mandatory_rules(context: AuthorizationContext, rules: tuple[AuthorizationRule, ...] = DEFAULT_AUTHORIZATION_RULES) -> tuple[RuleResult, ...]:
    results = tuple(rule.evaluate(context) for rule in rules)
    return results


def assert_mandatory_rules(context: AuthorizationContext, rules: tuple[AuthorizationRule, ...] = DEFAULT_AUTHORIZATION_RULES) -> None:
    results = evaluate_mandatory_rules(context, rules)
    for result in results:
        if not result.allowed:
            raise AuthorizationRuleViolation(f"{result.rule_id}: {result.reason}")
