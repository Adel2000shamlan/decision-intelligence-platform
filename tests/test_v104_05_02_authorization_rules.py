from uuid import uuid4
import pytest
from app.modules.authorization.domain import *
from app.modules.identity.domain.security_identity import SecurityIdentity, ActorContext


def ctx(permission="project:read", actor_type="human", assurance="standard", authenticated=True, resource_type=ResourceType.PROJECT, grants=None):
    uid, auth, tenant, corr = uuid4(), uuid4(), uuid4(), uuid4()
    identity = SecurityIdentity(uid, auth, assurance, authenticated)
    actor = ActorContext(uid, auth, corr, actor_type, authenticated)
    resource = Resource(resource_type, uuid4(), tenant)
    attrs = (("grants", ",".join(grants or ())),)
    return AuthorizationContext(identity, actor, tenant, Permission.parse(permission), resource, corr, attrs)


def test_authenticated_actor_rule_allows_authenticated_actor():
    assert AuthenticatedActorRule().evaluate(ctx()).allowed


def test_authenticated_actor_rule_denies_unauthenticated_actor():
    c = ctx(authenticated=False)
    assert not AuthenticatedActorRule().evaluate(c).allowed


def test_identity_consistency_rule():
    c = ctx(); assert IdentityConsistencyRule().evaluate(c).allowed
    bad = ActorContext(uuid4(), c.identity.authentication_id, c.correlation_id)
    object.__setattr__(c, "actor", bad)
    assert not IdentityConsistencyRule().evaluate(c).allowed


def test_tenant_binding_rule_denies_mismatch():
    c = ctx()
    object.__setattr__(c.resource, "tenant_id", uuid4())
    assert not TenantBindingRule().evaluate(c).allowed


def test_resource_action_compatibility_rule_denies_cross_resource_permission():
    assert not ResourceActionCompatibilityRule().evaluate(ctx("risk:read")).allowed


def test_sensitive_actions_require_human_strong_assurance():
    assert not SensitiveActionRule().evaluate(ctx("project:approve", assurance="standard")).allowed
    assert not SensitiveActionRule().evaluate(ctx("project:approve", actor_type="ai", assurance="strong")).allowed
    assert SensitiveActionRule().evaluate(ctx("project:approve", assurance="strong")).allowed


def test_non_sensitive_action_does_not_require_strong_assurance():
    assert SensitiveActionRule().evaluate(ctx("project:read")).allowed


def test_explicit_permission_requirement_rule_requires_exact_grant():
    rule = ExplicitPermissionRequirementRule()
    assert rule.evaluate(ctx("project:read", grants=("project:read",))).allowed
    assert not rule.evaluate(ctx("project:read", grants=("project:update",))).allowed


def test_rule_engine_is_deterministic_and_fail_closed():
    c = ctx("project:approve", assurance="standard")
    a = AuthorizationRuleEngine().evaluate(c); b = AuthorizationRuleEngine().evaluate(c)
    assert a == b and not a.allowed


def test_rule_engine_allows_safe_non_sensitive_context():
    c = ctx("project:read")
    assert AuthorizationRuleEngine().evaluate(c).allowed


def test_assert_mandatory_rules_raises_on_denial():
    with pytest.raises(AuthorizationRuleViolation):
        assert_mandatory_rules(ctx("project:execute", actor_type="ai", assurance="strong"))
