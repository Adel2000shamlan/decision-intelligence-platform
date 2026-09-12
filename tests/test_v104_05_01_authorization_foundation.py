from uuid import uuid4
import pytest

from app.modules.authorization.domain import (
    Action, ResourceType, Permission, Resource, AuthorizationContext,
    ExplicitPermissionPolicy, DefaultDenyPolicy, AuthorizationService,
    InvalidPermission, InvalidResource, InvalidAuthorizationContext,
)
from app.modules.identity.domain.security_identity import SecurityIdentity, ActorContext


def context(permission="project:read", tenant=True):
    uid = uuid4(); auth = uuid4(); tenant_id = uuid4() if tenant else None
    identity = SecurityIdentity(uid, auth)
    actor = ActorContext(uid, auth, uuid4())
    resource = Resource(ResourceType.PROJECT, uuid4(), tenant_id)
    return AuthorizationContext(identity, actor, tenant_id, Permission.parse(permission), resource, uuid4())


def test_action_and_resource_catalog_are_closed_enums():
    assert Action.READ.value == "read"
    assert ResourceType.PROJECT.value == "project"
    assert Action.EXECUTE.value == "execute"


def test_permission_has_canonical_key():
    p = Permission(ResourceType.PROJECT, Action.READ)
    assert p.key == "project:read"
    assert Permission.parse(" PROJECT:READ ") == p


def test_invalid_permission_is_rejected():
    with pytest.raises(InvalidPermission): Permission.parse("project")
    with pytest.raises((InvalidPermission, ValueError)): Permission.parse("unknown:read")


def test_resource_requires_uuid_and_valid_type():
    with pytest.raises(InvalidResource): Resource(ResourceType.PROJECT, "not-uuid")
    with pytest.raises((InvalidResource, ValueError)): Resource("unknown", uuid4())


def test_resource_can_be_tenant_scoped_or_global():
    assert Resource(ResourceType.PROJECT, uuid4(), uuid4()).tenant_id is not None
    assert Resource(ResourceType.KNOWLEDGE, uuid4()).tenant_id is None


def test_context_requires_matching_tenant_binding():
    c = context()
    object.__setattr__(c, "tenant_id", uuid4())
    with pytest.raises(InvalidAuthorizationContext):
        AuthorizationContext(c.identity, c.actor, c.tenant_id, c.permission, c.resource, c.correlation_id)


def test_context_requires_identity_actor_consistency():
    c = context()
    with pytest.raises(InvalidAuthorizationContext):
        AuthorizationContext(c.identity, ActorContext(uuid4(), c.identity.authentication_id, uuid4()), c.tenant_id, c.permission, c.resource, c.correlation_id)


def test_context_requires_authentication_identity_consistency():
    c = context()
    with pytest.raises(InvalidAuthorizationContext):
        AuthorizationContext(c.identity, ActorContext(c.identity.user_id, uuid4(), uuid4()), c.tenant_id, c.permission, c.resource, c.correlation_id)


def test_explicit_permission_policy_allows_only_explicit_grant():
    p = ExplicitPermissionPolicy(frozenset({"project:read"}))
    decision = p.evaluate(context("project:read"))
    assert decision.allowed is True
    assert decision.permission.key == "project:read"


def test_explicit_permission_policy_denies_missing_grant():
    p = ExplicitPermissionPolicy(frozenset({"project:read"}))
    decision = p.evaluate(context("project:update"))
    assert decision.allowed is False
    assert "not granted" in decision.reason


def test_policy_normalizes_grants():
    p = ExplicitPermissionPolicy(frozenset({" PROJECT:READ "}))
    assert p.grants == frozenset({"project:read"})


def test_default_deny_policy_is_deterministic():
    c = context("risk:read")
    a = DefaultDenyPolicy().evaluate(c)
    b = DefaultDenyPolicy().evaluate(c)
    assert a == b
    assert a.allowed is False


def test_authorization_service_uses_explicit_policy_then_default_deny():
    service = AuthorizationService((ExplicitPermissionPolicy(frozenset({"project:read"})),))
    assert service.authorize(context("project:read")).entity.allowed is True
    assert service.authorize(context("project:delete")).entity.allowed is False


def test_authorization_service_requires_authenticated_actor():
    c = context()
    unauth = ActorContext(c.identity.user_id, c.identity.authentication_id, c.correlation_id, authenticated=False)
    c2 = AuthorizationContext(c.identity, unauth, c.tenant_id, c.permission, c.resource, c.correlation_id)
    with pytest.raises(Exception):
        AuthorizationService().authorize(c2)


def test_require_raises_on_denial():
    with pytest.raises(Exception): AuthorizationService().require(context("project:read"))


def test_policy_decision_is_immutable():
    p = ExplicitPermissionPolicy(frozenset({"project:read"}))
    d = p.evaluate(context())
    with pytest.raises(Exception): d.allowed = False


def test_global_resource_context_is_supported():
    c = context("knowledge:read", tenant=False)
    resource = Resource(ResourceType.KNOWLEDGE, uuid4(), None)
    c = AuthorizationContext(c.identity, c.actor, None, Permission.parse("knowledge:read"), resource, c.correlation_id)
    assert AuthorizationService((ExplicitPermissionPolicy(frozenset({"knowledge:read"})),)).require(c).allowed
