from __future__ import annotations
from dataclasses import dataclass
from .models import AuthorizationContext, PolicyDecision
from .policy_engine import AuthorizationPolicyEngine
from .human_approval import HumanApprovalAuthorizationService
from .ai_boundary import AIAgentAuthorizationEngine
from .resource_authorization import ResourceResolver

@dataclass(frozen=True, slots=True)
class AuthorizationServices:
    policy_engine: AuthorizationPolicyEngine
    approval_service: HumanApprovalAuthorizationService = HumanApprovalAuthorizationService()
    ai_engine: AIAgentAuthorizationEngine = AIAgentAuthorizationEngine()
    def authorize(self, context: AuthorizationContext)->PolicyDecision: return self.policy_engine.evaluate(context)
    def require(self, context: AuthorizationContext)->PolicyDecision:
        d=self.authorize(context)
        if not d.allowed: raise PermissionError(d.reason)
        return d
    def authorize_human_approval(self, context: AuthorizationContext)->PolicyDecision: return self.approval_service.authorize(context)
    def require_human_approval(self, context: AuthorizationContext)->PolicyDecision: return self.approval_service.require(context)
    def authorize_ai(self, context: AuthorizationContext)->PolicyDecision: return self.ai_engine.evaluate(context)

def build_authorization_services(policies=(), resource_resolver: ResourceResolver|None=None)->AuthorizationServices:
    return AuthorizationServices(AuthorizationPolicyEngine(policies=tuple(policies),resource_resolver=resource_resolver))
