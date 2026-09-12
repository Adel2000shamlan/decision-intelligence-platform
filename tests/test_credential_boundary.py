import pytest
from dataclasses import dataclass
from uuid import uuid4
from app.shared.domain.errors import BusinessRuleViolation
from app.shared.domain.rules.engine import RuleContext
from app.modules.identity.domain.models import User
from app.modules.identity.domain.rules import USER_RULE_SET
from app.modules.identity.domain.security import CredentialBoundaryContract, CredentialBoundaryViolation, SecurityActorContext

def test_user_contains_no_credential_fields():
    u = User.create('boundary@example.com', 'Boundary')
    CredentialBoundaryContract.assert_user_boundary(u)
    USER_RULE_SET.assert_valid(u)

def test_user_rule_reports_credential_boundary_failure_without_mutating_user():
    u = User.create('boundary2@example.com', 'Boundary 2')
    u.__dict__['password_hash'] = 'secret'
    before = (u.status, u.version, u.updated_at)
    with pytest.raises(BusinessRuleViolation):
        USER_RULE_SET.assert_valid(u, RuleContext(operation='suspend'))
    assert (u.status, u.version, u.updated_at) == before

def test_boundary_rejects_declared_credential_material():
    @dataclass
    class FakeUser:
        id: object
        password_hash: str
    with pytest.raises(CredentialBoundaryViolation):
        CredentialBoundaryContract.assert_user_boundary(FakeUser(uuid4(), 'x'))

def test_event_boundary_rejects_credential_material():
    @dataclass
    class UnsafeEvent:
        event_id: object
        occurred_at: object
        aggregate_id: object
        actor_id: object
        token: str
    with pytest.raises(CredentialBoundaryViolation):
        CredentialBoundaryContract.assert_event_safe(UnsafeEvent(uuid4(), __import__('datetime').datetime.now(__import__('datetime').timezone.utc), uuid4(), None, 'secret'))

def test_security_actor_context_is_metadata_only():
    ctx = SecurityActorContext(actor_id=uuid4(), correlation_id=uuid4())
    assert ctx.actor_id is not None and ctx.correlation_id is not None
    assert not hasattr(ctx, 'password')
