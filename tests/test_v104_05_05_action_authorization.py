from uuid import uuid4
import pytest
from app.modules.authorization.domain import *
from app.modules.identity.domain.security_identity import SecurityIdentity, ActorContext


def ctx(action="read", actor_type="human", assurance="strong", authenticated=True):
    uid, auth, tenant, corr = uuid4(), uuid4(), uuid4(), uuid4()
    identity = SecurityIdentity(uid, auth, assurance, authenticated)
    actor = ActorContext(uid, auth, corr, actor_type, authenticated)
    resource = Resource(ResourceType.PROJECT, uuid4(), tenant)
    return AuthorizationContext(identity, actor, tenant, Permission(ResourceType.PROJECT, Action(action)), resource, corr)


def test_read_is_allowed_for_human():
    assert ActionAuthorizationEngine().evaluate(ctx("read")).allowed

@pytest.mark.parametrize("action", ["approve", "reject", "execute", "archive", "delete"])
def test_sensitive_actions_require_human_strong_assurance(action):
    assert ActionAuthorizationEngine().evaluate(ctx(action, "human", "strong")).allowed
    assert not ActionAuthorizationEngine().evaluate(ctx(action, "human", "standard")).allowed
    assert not ActionAuthorizationEngine().evaluate(ctx(action, "ai", "strong")).allowed

@pytest.mark.parametrize("action", ["approve", "reject", "execute", "archive", "delete"])
def test_ai_cannot_directly_perform_sensitive_actions(action):
    d = ActionAuthorizationEngine().evaluate(ctx(action, "ai", "strong"))
    assert not d.allowed and d.policy_id in {"auth.action.sensitive-actor.v1", "auth.action.ai-boundary.v1"}

@pytest.mark.parametrize("action", ["read", "create", "update"])
def test_ai_can_use_non_sensitive_actions(action):
    assert ActionAuthorizationEngine().evaluate(ctx(action, "ai", "standard")).allowed

def test_system_cannot_approve_or_reject():
    assert not ActionAuthorizationEngine().evaluate(ctx("approve", "system", "strong")).allowed
    assert not ActionAuthorizationEngine().evaluate(ctx("reject", "system", "strong")).allowed

def test_system_can_read():
    assert ActionAuthorizationEngine().evaluate(ctx("read", "system", "standard")).allowed

def test_policy_exception_fails_closed():
    class Broken:
        policy_id = "broken-action"
        def evaluate(self, context): raise RuntimeError("boom")
    d = ActionAuthorizationEngine((Broken(),)).evaluate(ctx())
    assert not d.allowed and d.policy_id == "broken-action"

def test_policy_must_return_decision():
    class Bad:
        policy_id = "bad-action"
        def evaluate(self, context): return True
    d = ActionAuthorizationEngine((Bad(),)).evaluate(ctx())
    assert not d.allowed

def test_action_gate_is_in_policy_engine_trace():
    c = ctx("read")
    result = AuthorizationPolicyEngine(policies=(ExplicitPermissionPolicy(frozenset({"project:read"})),)).evaluate_with_trace(c)
    assert result.decision.allowed
    assert [e.stage for e in result.evaluations] == ["mandatory-rule"] * 5 + ["action", "ai-boundary", "policy"]
    assert [e.sequence for e in result.evaluations] == list(range(1, 9))

def test_action_gate_runs_before_general_policy_for_valid_non_sensitive_action():
    c = ctx("read", "human", "strong")
    result = AuthorizationPolicyEngine(policies=(ExplicitPermissionPolicy(frozenset({"project:read"})),)).evaluate_with_trace(c)
    assert result.decision.allowed
    assert result.evaluations[-3].stage == "action"
    assert result.evaluations[-1].stage == "policy"
