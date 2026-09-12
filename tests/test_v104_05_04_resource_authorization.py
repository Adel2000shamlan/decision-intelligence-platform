from uuid import uuid4
import pytest
from app.modules.authorization.domain import *
from app.modules.identity.domain.security_identity import SecurityIdentity, ActorContext


def ctx(action="read", resource_type=ResourceType.PROJECT, owner=None):
    uid, auth, tenant, corr = uuid4(), uuid4(), uuid4(), uuid4()
    identity = SecurityIdentity(uid, auth, "strong", True)
    actor = ActorContext(uid, auth, corr, "human", True)
    r = Resource(resource_type, uuid4(), tenant, owner)
    return AuthorizationContext(identity, actor, tenant, Permission(resource_type, Action(action)), r, corr), uid


def test_resource_identity_is_immutable_and_supports_owner():
    c, uid = ctx(owner=None)
    assert c.resource.owner_id is None
    with pytest.raises(Exception): c.resource.owner_id = uid


def test_resolver_finds_exact_resource_projection():
    c, _ = ctx()
    record = ResourceRecord(c.resource)
    assert InMemoryResourceResolver((record,)).resolve(c.resource) == record
    assert InMemoryResourceResolver((record,)).resolve(Resource(ResourceType.PROJECT, uuid4(), c.tenant_id)) is None


def test_missing_resource_denies():
    c, _ = ctx()
    d = ResourceAuthorizationEngine(InMemoryResourceResolver()).evaluate(c)
    assert not d.allowed and d.policy_id == "auth.resource.exists.v1"


def test_active_resource_allows():
    c, _ = ctx()
    d = ResourceAuthorizationEngine(InMemoryResourceResolver((ResourceRecord(c.resource),))).evaluate(c)
    assert d.allowed


def test_archived_resource_denies():
    c, _ = ctx()
    record = ResourceRecord(c.resource, status=ResourceStatus.ARCHIVED)
    d = ResourceAuthorizationEngine(InMemoryResourceResolver((record,))).evaluate(c)
    assert not d.allowed


def test_nonexistent_record_denies():
    c, _ = ctx()
    record = ResourceRecord(c.resource, exists=False)
    d = ResourceAuthorizationEngine(InMemoryResourceResolver((record,))).evaluate(c)
    assert not d.allowed


def test_tenant_policy_denies_cross_tenant_projection():
    c, _ = ctx()
    other = Resource(c.resource.resource_type, c.resource.resource_id, uuid4())
    # Context construction blocks cross-tenant resources, so test policy in isolation with a controlled record.
    record = ResourceRecord(other)
    d = ResourceTenantPolicy().evaluate(c, record)
    assert not d.allowed


def test_type_policy_denies_mismatched_permission():
    c, _ = ctx(resource_type=ResourceType.PROJECT)
    bad = AuthorizationContext(c.identity, c.actor, c.tenant_id, Permission(ResourceType.RISK, Action.READ), c.resource, c.correlation_id)
    d = ResourceTypePolicy().evaluate(bad, ResourceRecord(c.resource))
    assert not d.allowed


def test_owner_policy_allows_owner_for_update():
    c, uid = ctx(action="update", owner=None)
    owned = Resource(c.resource.resource_type, c.resource.resource_id, c.tenant_id, uid)
    d = ResourceOwnerPolicy().evaluate(c, ResourceRecord(owned, owner_id=uid))
    assert d.allowed


def test_owner_policy_denies_non_owner_for_update():
    c, _ = ctx(action="update")
    d = ResourceOwnerPolicy().evaluate(c, ResourceRecord(c.resource, owner_id=uuid4()))
    assert not d.allowed


def test_owner_policy_not_applicable_to_read():
    c, _ = ctx(action="read")
    d = ResourceOwnerPolicy().evaluate(c, ResourceRecord(c.resource, owner_id=uuid4()))
    assert d.allowed


def test_owner_policy_not_applicable_without_owner_projection():
    c, _ = ctx(action="delete")
    d = ResourceOwnerPolicy().evaluate(c, ResourceRecord(c.resource))
    assert d.allowed


def test_resource_service_exposes_decision():
    c, _ = ctx()
    service = ResourceAuthorizationService(InMemoryResourceResolver((ResourceRecord(c.resource),)))
    result = service.authorize(c)
    assert result.entity.allowed


def test_resource_service_require_raises_for_missing_resource():
    c, _ = ctx()
    with pytest.raises(AuthorizationError):
        ResourceAuthorizationService(InMemoryResourceResolver()).require(c)


class BrokenResourcePolicy:
    policy_id = "broken-resource-policy"
    def evaluate(self, context, record):
        raise RuntimeError("boom")


def test_resource_policy_exception_fails_closed():
    c, _ = ctx()
    d = ResourceAuthorizationEngine(InMemoryResourceResolver((ResourceRecord(c.resource),)), (BrokenResourcePolicy(),)).evaluate(c)
    assert not d.allowed and d.policy_id == "broken-resource-policy"


def test_resource_policy_must_return_policy_decision():
    class Bad:
        policy_id = "bad"
        def evaluate(self, context, record): return True
    c, _ = ctx()
    d = ResourceAuthorizationEngine(InMemoryResourceResolver((ResourceRecord(c.resource),)), (Bad(),)).evaluate(c)
    assert not d.allowed


def test_resource_type_must_match_permission():
    c, _ = ctx()
    assert ResourceTypePolicy().evaluate(c, ResourceRecord(c.resource)).allowed


def test_resource_authorization_is_deterministic():
    c, _ = ctx()
    e = ResourceAuthorizationEngine(InMemoryResourceResolver((ResourceRecord(c.resource),)))
    assert e.evaluate(c) == e.evaluate(c)

def test_general_authorization_service_integrates_resource_gate():
    c, _ = ctx()
    from app.modules.authorization.domain import ExplicitPermissionPolicy
    service = AuthorizationService(
        (ExplicitPermissionPolicy(frozenset({"project:read"})),),
        resource_resolver=InMemoryResourceResolver((ResourceRecord(c.resource),)),
    )
    result = service.authorize(c)
    assert result.entity.allowed


def test_general_authorization_service_denies_missing_resource_before_policy_allow():
    c, _ = ctx()
    from app.modules.authorization.domain import ExplicitPermissionPolicy
    service = AuthorizationService(
        (ExplicitPermissionPolicy(frozenset({"project:read"})),),
        resource_resolver=InMemoryResourceResolver(),
    )
    result = service.authorize(c)
    assert not result.entity.allowed
    assert result.entity.policy_id == "auth.resource.exists.v1"


def test_resource_gate_is_visible_in_policy_engine_trace():
    c, _ = ctx()
    from app.modules.authorization.domain import ExplicitPermissionPolicy
    result = AuthorizationPolicyEngine(
        policies=(ExplicitPermissionPolicy(frozenset({"project:read"})),),
        resource_resolver=InMemoryResourceResolver((ResourceRecord(c.resource),)),
    ).evaluate_with_trace(c)
    assert result.decision.allowed
    assert [e.stage for e in result.evaluations] == ["mandatory-rule"] * 5 + ["action", "ai-boundary", "resource", "policy"]
    assert [e.sequence for e in result.evaluations] == list(range(1, 10))
