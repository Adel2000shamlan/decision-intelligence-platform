from uuid import uuid4
import pytest
from app.modules.authorization.domain import *
from app.modules.identity.domain.security_identity import SecurityIdentity, ActorContext


def ctx(permission="project:read", actor_type="human", assurance="standard", authenticated=True, grants=()):
    uid, auth, tenant, corr = uuid4(), uuid4(), uuid4(), uuid4()
    identity = SecurityIdentity(uid, auth, assurance, authenticated)
    actor = ActorContext(uid, auth, corr, actor_type, authenticated)
    resource = Resource(ResourceType.PROJECT, uuid4(), tenant)
    attrs = (("grants", ",".join(grants)),)
    return AuthorizationContext(identity, actor, tenant, Permission.parse(permission), resource, corr, attrs)


class AllowPolicy:
    policy_id = "test.allow.v1"
    def evaluate(self, context):
        return PolicyDecision(True, "test allow", self.policy_id, context.permission, context.correlation_id)


class DenyPolicy:
    policy_id = "test.deny.v1"
    def evaluate(self, context):
        return PolicyDecision(False, "test deny", self.policy_id, context.permission, context.correlation_id)


class BrokenPolicy:
    policy_id = "test.broken.v1"
    def evaluate(self, context):
        raise RuntimeError("boom")


def test_policy_engine_requires_mandatory_rules_before_policies():
    decision = AuthorizationPolicyEngine(policies=(AllowPolicy(),)).evaluate(ctx("project:approve", assurance="standard", grants=("project:approve",)))
    assert not decision.allowed
    assert decision.policy_id == "auth.sensitive-action.v1"


def test_policy_engine_allows_when_rules_and_policy_allow():
    decision = AuthorizationPolicyEngine(policies=(AllowPolicy(),)).evaluate(ctx())
    assert decision.allowed
    assert decision.policy_id == "test.allow.v1"


def test_policy_engine_default_denies_without_allow_policy():
    decision = AuthorizationPolicyEngine().evaluate(ctx())
    assert not decision.allowed
    assert decision.policy_id == "default-deny-v1"


def test_policy_engine_denies_on_first_policy_deny():
    decision = AuthorizationPolicyEngine(policies=(DenyPolicy(), AllowPolicy())).evaluate(ctx())
    assert not decision.allowed
    assert decision.policy_id == "test.deny.v1"


def test_policy_engine_policy_exception_fails_closed():
    decision = AuthorizationPolicyEngine(policies=(BrokenPolicy(),)).evaluate(ctx())
    assert not decision.allowed
    assert decision.policy_id == "test.broken.v1"
    assert decision.reason == "authorization policy evaluation failed"


def test_policy_engine_trace_is_ordered_and_complete():
    result = AuthorizationPolicyEngine(policies=(AllowPolicy(),)).evaluate_with_trace(ctx())
    assert result.decision.allowed
    assert [x.stage for x in result.evaluations] == ["mandatory-rule"] * 5 + ["action", "ai-boundary", "policy"]
    assert [x.sequence for x in result.evaluations] == [1, 2, 3, 4, 5, 6, 7, 8]


def test_policy_engine_trace_stops_at_mandatory_failure():
    result = AuthorizationPolicyEngine(policies=(AllowPolicy(),)).evaluate_with_trace(ctx("project:execute", actor_type="ai", assurance="strong", grants=("project:execute",)))
    assert not result.decision.allowed
    assert result.evaluations[-1].stage == "mandatory-rule"
    assert all(x.stage != "policy" for x in result.evaluations)


def test_policy_engine_require_raises_on_denial():
    with pytest.raises(AuthorizationError):
        AuthorizationPolicyEngine().require(ctx())


def test_authorization_service_uses_policy_engine():
    service = AuthorizationService((ExplicitPermissionPolicy(frozenset({"project:read"})),))
    result = service.authorize(ctx())
    assert result.entity is not None and result.entity.allowed


def test_legacy_rule_engine_alias_remains_compatible():
    assert AuthorizationRuleEngine().evaluate(ctx()).allowed
