from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from uuid import UUID
from .models import Action, AuthorizationContext, PolicyDecision, ResourceType

class ApprovalAuthorizationError(Exception): pass
class ApprovalStatus(str, Enum): PENDING="pending"; APPROVED="approved"; REJECTED="rejected"; CANCELLED="cancelled"; EXPIRED="expired"

@dataclass(frozen=True, slots=True)
class ApprovalRequest:
    approval_id: UUID
    resource_type: ResourceType
    resource_id: UUID
    tenant_id: UUID | None
    requested_by: UUID
    correlation_id: UUID
    status: ApprovalStatus = ApprovalStatus.PENDING
    def __post_init__(self):
        if not isinstance(self.approval_id, UUID) or not isinstance(self.resource_id, UUID) or not isinstance(self.requested_by, UUID) or not isinstance(self.correlation_id, UUID): raise ApprovalAuthorizationError("approval identifiers must be UUID")
        object.__setattr__(self,"resource_type",ResourceType(self.resource_type)); object.__setattr__(self,"status",ApprovalStatus(self.status))
        if self.tenant_id is not None and not isinstance(self.tenant_id, UUID): raise ApprovalAuthorizationError("tenant_id must be UUID or None")

@dataclass(frozen=True, slots=True)
class HumanApprovalPolicy:
    policy_id: str = "auth.human-approval.v1"
    def evaluate(self, context: AuthorizationContext) -> PolicyDecision:
        action=context.permission.action
        allowed=(action in {Action.APPROVE,Action.REJECT} and context.actor.actor_type=="human" and context.actor.authenticated and context.identity.authenticated and context.identity.assurance_level=="strong" and context.resource.resource_type in {ResourceType.DECISION,ResourceType.SCENARIO})
        reason="human strong-assurance approval actor accepted" if allowed else "approval requires authenticated human with strong assurance on decision or scenario"
        return PolicyDecision(allowed,reason,self.policy_id,context.permission,context.correlation_id)

@dataclass(frozen=True, slots=True)
class HumanApprovalAuthorizationService:
    policy: HumanApprovalPolicy = HumanApprovalPolicy()
    def authorize(self, context: AuthorizationContext) -> PolicyDecision: return self.policy.evaluate(context)
    def require(self, context: AuthorizationContext) -> PolicyDecision:
        d=self.authorize(context)
        if not d.allowed: raise ApprovalAuthorizationError(d.reason)
        return d
