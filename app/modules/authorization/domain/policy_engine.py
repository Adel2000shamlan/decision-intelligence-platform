from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable

from .models import AuthorizationContext, AuthorizationPolicy, DefaultDenyPolicy, PolicyDecision
from .rules import AuthorizationRule, DEFAULT_AUTHORIZATION_RULES, evaluate_mandatory_rules
from .resource_authorization import ResourceAuthorizationEngine, ResourceResolver
from .action_authorization import ActionAuthorizationEngine
from .ai_boundary import AIAgentAuthorizationEngine


@dataclass(frozen=True, slots=True)
class PolicyEvaluation:
    """Immutable, auditable result of one policy evaluation."""
    decision: PolicyDecision
    stage: str
    sequence: int


@dataclass(frozen=True, slots=True)
class AuthorizationEvaluation:
    """Complete deterministic authorization trace; safe to expose to audit layers."""
    decision: PolicyDecision
    evaluations: tuple[PolicyEvaluation, ...]


@dataclass(frozen=True, slots=True)
class AuthorizationPolicyEngine:
    """Deterministic policy engine with mandatory-rule gating and fail-closed behavior.

    Order is explicit: mandatory security rules -> configured policies -> default deny.
    The first mandatory failure is terminal. Among policies, any explicit deny wins;
    otherwise the first allow wins. Policy exceptions are converted to deny.
    """
    rules: tuple[AuthorizationRule, ...] = DEFAULT_AUTHORIZATION_RULES
    policies: tuple[AuthorizationPolicy, ...] = ()
    default_deny: AuthorizationPolicy = DefaultDenyPolicy()
    resource_resolver: ResourceResolver | None = None

    def evaluate(self, context: AuthorizationContext) -> PolicyDecision:
        return self.evaluate_with_trace(context).decision

    def evaluate_with_trace(self, context: AuthorizationContext) -> AuthorizationEvaluation:
        evaluations: list[PolicyEvaluation] = []
        sequence = 0

        for result in evaluate_mandatory_rules(context, self.rules):
            sequence += 1
            decision = PolicyDecision(
                allowed=result.allowed,
                reason=result.reason,
                policy_id=result.rule_id,
                permission=context.permission,
                correlation_id=context.correlation_id,
            )
            evaluations.append(PolicyEvaluation(decision, "mandatory-rule", sequence))
            if not result.allowed:
                return AuthorizationEvaluation(decision, tuple(evaluations))

        sequence += 1
        action_decision = ActionAuthorizationEngine().evaluate(context)
        evaluations.append(PolicyEvaluation(action_decision, "action", sequence))
        if not action_decision.allowed:
            return AuthorizationEvaluation(action_decision, tuple(evaluations))

        sequence += 1
        ai_decision = AIAgentAuthorizationEngine().evaluate(context)
        evaluations.append(PolicyEvaluation(ai_decision, "ai-boundary", sequence))
        if not ai_decision.allowed:
            return AuthorizationEvaluation(ai_decision, tuple(evaluations))

        if self.resource_resolver is not None:
            sequence += 1
            resource_decision = ResourceAuthorizationEngine(self.resource_resolver).evaluate(context)
            evaluations.append(PolicyEvaluation(resource_decision, "resource", sequence))
            if not resource_decision.allowed:
                return AuthorizationEvaluation(resource_decision, tuple(evaluations))

        first_allow: PolicyDecision | None = None
        for policy in self.policies:
            sequence += 1
            try:
                decision = policy.evaluate(context)
                if not isinstance(decision, PolicyDecision):
                    raise TypeError("authorization policy must return PolicyDecision")
            except Exception:
                decision = PolicyDecision(
                    allowed=False,
                    reason="authorization policy evaluation failed",
                    policy_id=getattr(policy, "policy_id", "unknown-policy"),
                    permission=context.permission,
                    correlation_id=context.correlation_id,
                )
            evaluations.append(PolicyEvaluation(decision, "policy", sequence))
            if not decision.allowed:
                return AuthorizationEvaluation(decision, tuple(evaluations))
            if first_allow is None:
                first_allow = decision

        if first_allow is not None:
            return AuthorizationEvaluation(first_allow, tuple(evaluations))

        sequence += 1
        decision = self.default_deny.evaluate(context)
        evaluations.append(PolicyEvaluation(decision, "default-deny", sequence))
        return AuthorizationEvaluation(decision, tuple(evaluations))

    def require(self, context: AuthorizationContext) -> PolicyDecision:
        decision = self.evaluate(context)
        if not decision.allowed:
            from .models import AuthorizationError
            raise AuthorizationError(decision.reason)
        return decision


@dataclass(frozen=True, slots=True)
class AuthorizationRuleEngine:
    """V104.05.02 compatibility engine: evaluates mandatory rules only."""
    rules: tuple[AuthorizationRule, ...] = DEFAULT_AUTHORIZATION_RULES

    def evaluate(self, context: AuthorizationContext) -> PolicyDecision:
        for result in evaluate_mandatory_rules(context, self.rules):
            if not result.allowed:
                return PolicyDecision(False, result.reason, result.rule_id, context.permission, context.correlation_id)
        return PolicyDecision(True, "mandatory authorization rules satisfied", "authorization-rules-v1", context.permission, context.correlation_id)
