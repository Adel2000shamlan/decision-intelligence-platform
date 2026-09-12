from uuid import uuid4
from datetime import datetime, timezone
from app.modules.identity.domain.models import User
from app.modules.identity.domain.security_rules import SECURITY_RULE_SET
from app.modules.identity.domain.rules import USER_RULE_SET
from app.modules.identity.domain.audit import SecurityAuditEvent

def test_security_rules_are_registered(): assert len(SECURITY_RULE_SET.rules)==3

def test_user_rules_include_credential_boundary(): assert any(r.code=='identity.user.credential_boundary' for r in USER_RULE_SET.rules)

def test_user_event_types_are_safe():
    u=User.create('safe@example.com','Safe'); events=u.pull_events(); assert events and all(not hasattr(e,'password') for e in events)

def test_audit_event_has_no_secret_material():
    e=SecurityAuditEvent(uuid4(),'authentication.failed',datetime.now(timezone.utc),None,uuid4(),uuid4(),'failure'); assert not hasattr(e,'password')
