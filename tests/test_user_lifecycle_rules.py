import pytest
from uuid import uuid4
from app.shared.domain.errors import BusinessRuleViolation
from app.shared.domain.rules.engine import RuleContext
from app.modules.identity.domain.models import User, UserStatus
from app.modules.identity.domain.rules import USER_RULE_SET
from app.modules.identity.domain.services import UserLifecycleService
from app.modules.identity import InMemoryUserRepository

def user(): return User.create('rules@example.com','Rules User')

def test_rule_set_passes_for_valid_user():
    u=user(); USER_RULE_SET.assert_valid(u)

def test_transition_rules_allow_only_expected_sources():
    u=user(); USER_RULE_SET.assert_valid(u, RuleContext(operation='suspend'))
    u.suspend(); u.pull_events()
    USER_RULE_SET.assert_valid(u, RuleContext(operation='reactivate'))
    u.reactivate(); u.pull_events(); u.archive()
    USER_RULE_SET.assert_valid(u)
    with pytest.raises(BusinessRuleViolation): USER_RULE_SET.assert_valid(u, RuleContext(operation='reactivate'))

def test_service_checks_rule_before_mutation():
    repo=InMemoryUserRepository(); service=UserLifecycleService(); u=service.create(repo,'atomic@example.com','Atomic').entity; u.pull_events()
    u.suspend(); u.pull_events()
    before=(u.status,u.version,u.updated_at)
    with pytest.raises(BusinessRuleViolation): service.suspend(repo,u.id,expected_version=u.version)
    assert (u.status,u.version,u.updated_at)==before

def test_archived_terminal_rule_blocks_rename_at_rule_boundary():
    u=user(); u.archive(); u.pull_events()
    with pytest.raises(BusinessRuleViolation): USER_RULE_SET.assert_valid(u, RuleContext(operation='rename'))
