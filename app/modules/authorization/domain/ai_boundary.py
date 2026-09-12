from __future__ import annotations
from dataclasses import dataclass
from .models import Action, AuthorizationContext, PolicyDecision

AI_SENSITIVE_ACTIONS=frozenset({Action.APPROVE,Action.REJECT,Action.EXECUTE,Action.ARCHIVE,Action.DELETE})
AI_PROPOSAL_ACTIONS=frozenset({Action.READ,Action.CREATE,Action.UPDATE})

@dataclass(frozen=True, slots=True)
class AIAgentBoundaryPolicy:
    policy_id: str = "auth.ai-agent.boundary.v1"
    def evaluate(self, context: AuthorizationContext) -> PolicyDecision:
        if context.actor.actor_type != "ai": return PolicyDecision(True,"AI boundary not applicable",self.policy_id,context.permission,context.correlation_id)
        allowed=context.permission.action in AI_PROPOSAL_ACTIONS
        return PolicyDecision(allowed,"AI action is proposal/analysis scoped" if allowed else "AI agent cannot directly perform privileged human-governed action",self.policy_id,context.permission,context.correlation_id)

@dataclass(frozen=True, slots=True)
class AIAgentIdentityPolicy:
    policy_id: str = "auth.ai-agent.identity.v1"
    def evaluate(self, context: AuthorizationContext) -> PolicyDecision:
        if context.actor.actor_type != "ai": return PolicyDecision(True,"AI identity rule not applicable",self.policy_id,context.permission,context.correlation_id)
        allowed=context.actor.authenticated and context.identity.authenticated and context.identity.user_id==context.actor.actor_id and context.identity.authentication_id==context.actor.authentication_id
        return PolicyDecision(allowed,"AI actor identity is authenticated and consistent" if allowed else "AI actor identity is invalid or unauthenticated",self.policy_id,context.permission,context.correlation_id)

DEFAULT_AI_BOUNDARY_POLICIES=(AIAgentIdentityPolicy(),AIAgentBoundaryPolicy())

@dataclass(frozen=True, slots=True)
class AIAgentAuthorizationEngine:
    policies: tuple=DEFAULT_AI_BOUNDARY_POLICIES
    def evaluate(self, context: AuthorizationContext) -> PolicyDecision:
        for policy in self.policies:
            try:
                d=policy.evaluate(context)
                if not isinstance(d,PolicyDecision): raise TypeError
            except Exception:
                return PolicyDecision(False,"AI authorization evaluation failed",getattr(policy,"policy_id","unknown-ai-policy"),context.permission,context.correlation_id)
            if not d.allowed:return d
        return PolicyDecision(True,"AI agent boundary satisfied","ai-agent-authorization-v1",context.permission,context.correlation_id)
