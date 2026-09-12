from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol

from .models import Action, AuthorizationContext, PolicyDecision


class ActionAuthorizationPolicy(Protocol):
    policy_id: str
    def evaluate(self, context: AuthorizationContext) -> PolicyDecision: ...


SENSITIVE_ACTIONS = frozenset({Action.APPROVE, Action.REJECT, Action.EXECUTE, Action.ARCHIVE, Action.DELETE})
AI_FORBIDDEN_ACTIONS = frozenset({Action.APPROVE, Action.REJECT, Action.EXECUTE, Action.ARCHIVE, Action.DELETE})
SYSTEM_FORBIDDEN_ACTIONS = frozenset({Action.APPROVE, Action.REJECT})


@dataclass(frozen=True, slots=True)
class ActionSupportedPolicy:
    """Ensures the requested action is one of the canonical authorization actions."""
    policy_id: str = "auth.action.supported.v1"
    def evaluate(self, context: AuthorizationContext) -> PolicyDecision:
        allowed = isinstance(context.permission.action, Action)
        return PolicyDecision(allowed, "action is supported" if allowed else "action is unsupported", self.policy_id, context.permission, context.correlation_id)


@dataclass(frozen=True, slots=True)
class SensitiveActionActorPolicy:
    """Sensitive actions require a human actor with strong assurance."""
    policy_id: str = "auth.action.sensitive-actor.v1"
    def evaluate(self, context: AuthorizationContext) -> PolicyDecision:
        if context.permission.action not in SENSITIVE_ACTIONS:
            return PolicyDecision(True, "sensitive-action restriction not applicable", self.policy_id, context.permission, context.correlation_id)
        allowed = context.actor.actor_type == "human" and context.identity.assurance_level == "strong" and context.actor.authenticated and context.identity.authenticated
        return PolicyDecision(allowed, "sensitive action has required human strong-assurance actor" if allowed else "sensitive action requires authenticated human with strong assurance", self.policy_id, context.permission, context.correlation_id)


@dataclass(frozen=True, slots=True)
class AIActionBoundaryPolicy:
    """AI actors may not perform irreversible/high-impact actions directly."""
    policy_id: str = "auth.action.ai-boundary.v1"
    def evaluate(self, context: AuthorizationContext) -> PolicyDecision:
        if context.actor.actor_type != "ai":
            return PolicyDecision(True, "AI action restriction not applicable", self.policy_id, context.permission, context.correlation_id)
        allowed = context.permission.action not in AI_FORBIDDEN_ACTIONS
        return PolicyDecision(allowed, "AI actor action is within delegated boundary" if allowed else "AI actor cannot directly perform this action", self.policy_id, context.permission, context.correlation_id)


@dataclass(frozen=True, slots=True)
class SystemActionBoundaryPolicy:
    """System actors cannot directly make human approval/rejection decisions."""
    policy_id: str = "auth.action.system-boundary.v1"
    def evaluate(self, context: AuthorizationContext) -> PolicyDecision:
        if context.actor.actor_type != "system":
            return PolicyDecision(True, "system action restriction not applicable", self.policy_id, context.permission, context.correlation_id)
        allowed = context.permission.action not in SYSTEM_FORBIDDEN_ACTIONS
        return PolicyDecision(allowed, "system actor action is within system boundary" if allowed else "system actor cannot approve or reject", self.policy_id, context.permission, context.correlation_id)


DEFAULT_ACTION_POLICIES: tuple[ActionAuthorizationPolicy, ...] = (
    ActionSupportedPolicy(),
    SensitiveActionActorPolicy(),
    AIActionBoundaryPolicy(),
    SystemActionBoundaryPolicy(),
)


@dataclass(frozen=True, slots=True)
class ActionAuthorizationEngine:
    policies: tuple[ActionAuthorizationPolicy, ...] = DEFAULT_ACTION_POLICIES
    def evaluate(self, context: AuthorizationContext) -> PolicyDecision:
        for policy in self.policies:
            try:
                decision = policy.evaluate(context)
                if not isinstance(decision, PolicyDecision):
                    raise TypeError("action authorization policy must return PolicyDecision")
            except Exception:
                return PolicyDecision(False, "action authorization policy evaluation failed", getattr(policy, "policy_id", "unknown-action-policy"), context.permission, context.correlation_id)
            if not decision.allowed:
                return decision
        return PolicyDecision(True, "action authorization policies satisfied", "action-authorization-v1", context.permission, context.correlation_id)
