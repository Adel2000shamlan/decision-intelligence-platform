from __future__ import annotations
from dataclasses import dataclass
from app.shared.domain.rules.engine import RuleContext, RuleResult, RuleSet
from app.shared.domain.errors import UnauthorizedDomainAction
from .models import User, UserStatus
from .security_identity import ActorContext

@dataclass(frozen=True)
class UserSecurityIdentityRule:
    code='identity.user.security_identity'
    def check(self,target:User,context:RuleContext)->RuleResult:
        ok=target.id is not None
        return RuleResult(self.code,'security identity is stable' if ok else 'user id is required',ok)
@dataclass(frozen=True)
class AuthenticatedActorRule:
    code='identity.user.authenticated_actor'
    def check(self,target:User,context:RuleContext)->RuleResult:
        if context.operation != 'sensitive': return RuleResult(self.code,'actor not required',True)
        ok=context.actor_id is not None
        return RuleResult(self.code,'authenticated actor present' if ok else 'authenticated actor required',ok)
@dataclass(frozen=True)
class UserActiveAuthenticationRule:
    code='identity.user.active_for_authentication'
    def check(self,target:User,context:RuleContext)->RuleResult:
        if context.operation != 'authenticate': return RuleResult(self.code,'not an authentication attempt',True)
        ok=target.status is UserStatus.ACTIVE
        return RuleResult(self.code,'user may authenticate' if ok else 'user is not active',ok)
SECURITY_RULE_SET=RuleSet((UserSecurityIdentityRule(),AuthenticatedActorRule(),UserActiveAuthenticationRule()))
