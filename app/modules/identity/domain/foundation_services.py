from __future__ import annotations
from uuid import UUID, uuid4
from datetime import datetime, timezone
from app.shared.domain.errors import BusinessRuleViolation
from app.shared.domain.rules.engine import RuleContext
from .models import User
from .security import SecurityActorContext
from .security_identity import SecurityIdentity, ActorContext
from .credentials import CredentialOwnershipContract, CredentialReference
from .lockout import AuthenticationFailureState, AuthenticationFailureService
from .audit import SecurityAuditEvent, SecurityAuditSink
from .security_rules import SECURITY_RULE_SET

class AuthenticationFoundationService:
    def __init__(self, audit_sink: SecurityAuditSink | None=None, failure_service: AuthenticationFailureService | None=None):
        self.audit_sink=audit_sink; self.failure_service=failure_service or AuthenticationFailureService()
    def resolve_identity(self,user:User,authentication_id:UUID,*,assurance_level='standard')->SecurityIdentity:
        SECURITY_RULE_SET.assert_valid(user,RuleContext(operation='authenticate'))
        identity=SecurityIdentity(user.id,authentication_id,assurance_level,True)
        self._audit('identity.resolved',None,user.id,'success')
        return identity
    def assert_authentication_allowed(self,user:User,credential_exists:bool,state:AuthenticationFailureState|None=None)->None:
        SECURITY_RULE_SET.assert_valid(user,RuleContext(operation='authenticate'))
        CredentialOwnershipContract.assert_user_can_authenticate(user,credential_exists)
        if state: self.failure_service.assert_allowed(state)
    def authenticate_failure(self,user:User,state:AuthenticationFailureState,correlation_id:UUID|None=None)->AuthenticationFailureState:
        new=self.failure_service.record_failure(state); self._audit('authentication.failed',None,user.id,'failure',correlation_id); return new
    def authenticate_success(self,user:User,state:AuthenticationFailureState,correlation_id:UUID|None=None)->AuthenticationFailureState:
        new=self.failure_service.record_success(state); self._audit('authentication.succeeded',None,user.id,'success',correlation_id); return new
    def build_actor_context(self,identity:SecurityIdentity,correlation_id:UUID|None=None)->ActorContext:
        return ActorContext(identity.user_id,identity.authentication_id,correlation_id or uuid4(),'human',identity.authenticated)
    def _audit(self,event_type,actor_id,target_user_id,outcome,correlation_id=None):
        if self.audit_sink: self.audit_sink.record(SecurityAuditEvent(uuid4(),event_type,datetime.now(timezone.utc),actor_id,target_user_id,correlation_id or uuid4(),outcome))
