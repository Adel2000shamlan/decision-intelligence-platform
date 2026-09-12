from datetime import datetime, timezone, timedelta
from uuid import uuid4
import pytest
from app.modules.identity.domain.models import User, UserStatus
from app.modules.identity.domain.security import CredentialBoundaryContract, CredentialBoundaryViolation, SecurityActorContext
from app.modules.identity.domain.security_identity import SecurityIdentity, ActorContext
from app.modules.identity.domain.credentials import CredentialReference, CredentialStatus, CredentialOwnershipContract
from app.modules.identity.domain.lockout import AuthenticationFailureState, AuthenticationFailureService, LockoutPolicy
from app.modules.identity.domain.audit import SecurityAuditEvent, InMemorySecurityAuditSink
from app.modules.identity.domain.foundation_services import AuthenticationFoundationService


def user(): return User.create('a@example.com','Alice')

def test_security_identity_separates_user_and_authentication_ids():
    u=user(); i=SecurityIdentity(u.id,uuid4()); assert i.user_id==u.id and i.authentication_id!=u.id

def test_actor_context_requires_authentication():
    c=ActorContext(None,None,uuid4(),authenticated=False)
    with pytest.raises(Exception): c.require_authenticated()

def test_security_actor_context_contains_only_allowed_metadata():
    c=SecurityActorContext(uuid4(),uuid4()); assert c.actor_id and c.correlation_id

def test_credential_boundary_rejects_declared_field():
    class Bad:
        password='x'
    with pytest.raises(CredentialBoundaryViolation): CredentialBoundaryContract.assert_user_boundary(Bad())

def test_user_boundary_has_no_credential_fields():
    u=user(); CredentialBoundaryContract.assert_user_boundary(u)

def test_credential_reference_contains_metadata_not_secret():
    r=CredentialReference(uuid4(),uuid4(),'password',CredentialStatus.ACTIVE); CredentialOwnershipContract.assert_reference_safe(r)

def test_revoked_credential_rejected():
    r=CredentialReference(uuid4(),uuid4(),'password',CredentialStatus.REVOKED)
    with pytest.raises(Exception): CredentialOwnershipContract.assert_reference_safe(r)

def test_inactive_user_cannot_authenticate():
    u=user(); u.suspend()
    with pytest.raises(Exception): CredentialOwnershipContract.assert_user_can_authenticate(u,True)

def test_lockout_threshold_and_expiry():
    s=AuthenticationFailureState(uuid4()); svc=AuthenticationFailureService(LockoutPolicy(3,60));
    s=svc.record_failure(s); s=svc.record_failure(s); s=svc.record_failure(s)
    assert s.locked_until is not None and s.failed_attempts==0
    with pytest.raises(Exception): svc.assert_allowed(s)
    unlocked=AuthenticationFailureState(s.user_id,0,datetime.now(timezone.utc)-timedelta(seconds=1),s.lock_count,s.version)
    svc.assert_allowed(unlocked)

def test_success_resets_failures():
    uid=uuid4(); svc=AuthenticationFailureService(); s=AuthenticationFailureState(uid,2); n=svc.record_success(s); assert n.failed_attempts==0

def test_audit_event_rejects_credential_field():
    class BadAudit:
        password='x'
    with pytest.raises(CredentialBoundaryViolation): CredentialBoundaryContract.assert_event_safe(BadAudit())

def test_audit_sink_records_safe_event():
    sink=InMemorySecurityAuditSink(); e=SecurityAuditEvent(uuid4(),'authentication.succeeded',datetime.now(timezone.utc),uuid4(),uuid4(),uuid4(),'success'); sink.record(e); assert len(sink.events)==1

def test_foundation_resolves_identity_and_builds_actor():
    u=user(); svc=AuthenticationFoundationService(); i=svc.resolve_identity(u,uuid4()); c=svc.build_actor_context(i); c.require_authenticated(); assert c.actor_id==u.id

def test_foundation_rejects_locked_authentication():
    u=user(); fs=AuthenticationFailureState(u.id,0,datetime.now(timezone.utc)+timedelta(minutes=1)); svc=AuthenticationFoundationService()
    with pytest.raises(Exception): svc.assert_authentication_allowed(u,True,fs)
