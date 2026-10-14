from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from app.modules.authorization.domain.models import (
    Action,
    Permission,
    PolicyDecision,
    Resource,
    ResourceType,
)
from app.modules.authorization.domain.authorization_services import (
    AuthorizationServices,
)
from app.modules.developer.authorization.adapter import (
    DeveloperAuthorizationError,
    DeveloperAuthorizationService,
)
from app.modules.developer.domain.models import (
    APIScope,
    DeveloperCredential,
)
from app.modules.developer.security.credentials import (
    DeveloperCredentialSecurityService,
)


class AllowAllAuthorization:
    def authorize(self, context):
        return PolicyDecision(
            allowed=True,
            reason="allowed",
            policy_id="test-allow",
            permission=context.permission,
            correlation_id=context.correlation_id,
        )


class DenyAuthorization:
    def authorize(self, context):
        return PolicyDecision(
            allowed=False,
            reason="authorization denied",
            policy_id="test-deny",
            permission=context.permission,
            correlation_id=context.correlation_id,
        )


@pytest.fixture
def security():
    return DeveloperCredentialSecurityService()


@pytest.fixture
def ids():
    return {
        "tenant": uuid4(),
        "other_tenant": uuid4(),
        "user": uuid4(),
        "auth": uuid4(),
        "application": uuid4(),
    }


def make_credential(security, ids, scopes, expires_at=None):
    return security.issue(
        tenant_id=ids["tenant"],
        application_id=ids["application"],
        client_id=f"client-{uuid4()}",
        scopes=scopes,
        expires_at=expires_at,
    )


def make_service(authorization):
    return DeveloperAuthorizationService.create(
        authorization=authorization,
    )


def resource(ids, resource_type=ResourceType.PROJECT, tenant=None):
    return Resource(
        resource_type=resource_type,
        resource_id=uuid4(),
        tenant_id=ids["tenant"] if tenant is None else tenant,
    )


def test_required_scope_read_and_write():
    assert (
        DeveloperAuthorizationService.required_scope(
            ResourceType.PROJECT,
            Action.READ,
        )
        is APIScope.PROJECTS_READ
    )

    assert (
        DeveloperAuthorizationService.required_scope(
            ResourceType.PROJECT,
            Action.CREATE,
        )
        is APIScope.PROJECTS_WRITE
    )

    assert (
        DeveloperAuthorizationService.required_scope(
            ResourceType.DECISION,
            Action.UPDATE,
        )
        is APIScope.DECISIONS_WRITE
    )

    assert (
        DeveloperAuthorizationService.required_scope(
            ResourceType.RISK,
            Action.DELETE,
        )
        is APIScope.RISKS_WRITE
    )


@pytest.mark.parametrize(
    "action",
    [
        Action.APPROVE,
        Action.REJECT,
        Action.EXECUTE,
        Action.ARCHIVE,
    ],
)
def test_sensitive_actions_are_not_granted_by_developer_write_scope(action):
    with pytest.raises(DeveloperAuthorizationError):
        DeveloperAuthorizationService.required_scope(
            ResourceType.PROJECT,
            action,
        )


def test_valid_read_scope_reaches_existing_authorization_engine(security, ids):
    issued = make_credential(
        security,
        ids,
        (APIScope.PROJECTS_READ,),
    )

    service = make_service(AllowAllAuthorization())

    decision = service.require(
        credential=issued.credential,
        secret=issued.secret,
        user_id=ids["user"],
        authentication_id=ids["auth"],
        tenant_id=ids["tenant"],
        resource=resource(ids),
        action=Action.READ,
    )

    assert decision.allowed is True
    assert decision.policy_id == "test-allow"


def test_valid_write_scope_reaches_existing_authorization_engine(security, ids):
    issued = make_credential(
        security,
        ids,
        (APIScope.PROJECTS_WRITE,),
    )

    service = make_service(AllowAllAuthorization())

    decision = service.require(
        credential=issued.credential,
        secret=issued.secret,
        user_id=ids["user"],
        authentication_id=ids["auth"],
        tenant_id=ids["tenant"],
        resource=resource(ids),
        action=Action.UPDATE,
    )

    assert decision.allowed is True


def test_missing_scope_is_denied_before_authorization_engine(security, ids):
    issued = make_credential(
        security,
        ids,
        (APIScope.PROJECTS_READ,),
    )

    service = make_service(DenyAuthorization())

    with pytest.raises(DeveloperAuthorizationError, match="missing scope"):
        service.require(
            credential=issued.credential,
            secret=issued.secret,
            user_id=ids["user"],
            authentication_id=ids["auth"],
            tenant_id=ids["tenant"],
            resource=resource(ids),
            action=Action.CREATE,
        )


def test_wrong_secret_is_denied(security, ids):
    issued = make_credential(
        security,
        ids,
        (APIScope.PROJECTS_READ,),
    )

    service = make_service(AllowAllAuthorization())

    with pytest.raises(DeveloperAuthorizationError, match="invalid developer credential"):
        service.require(
            credential=issued.credential,
            secret="wrong-secret",
            user_id=ids["user"],
            authentication_id=ids["auth"],
            tenant_id=ids["tenant"],
            resource=resource(ids),
            action=Action.READ,
        )


def test_tenant_mismatch_is_denied(security, ids):
    issued = make_credential(
        security,
        ids,
        (APIScope.PROJECTS_READ,),
    )

    service = make_service(AllowAllAuthorization())

    with pytest.raises(DeveloperAuthorizationError, match="tenant mismatch"):
        service.require(
            credential=issued.credential,
            secret=issued.secret,
            user_id=ids["user"],
            authentication_id=ids["auth"],
            tenant_id=ids["other_tenant"],
            resource=resource(ids),
            action=Action.READ,
        )


def test_resource_tenant_mismatch_is_denied(security, ids):
    issued = make_credential(
        security,
        ids,
        (APIScope.PROJECTS_READ,),
    )

    service = make_service(AllowAllAuthorization())

    with pytest.raises(DeveloperAuthorizationError, match="resource tenant mismatch"):
        service.require(
            credential=issued.credential,
            secret=issued.secret,
            user_id=ids["user"],
            authentication_id=ids["auth"],
            tenant_id=ids["tenant"],
            resource=resource(
                ids,
                tenant=ids["other_tenant"],
            ),
            action=Action.READ,
        )


def test_revoked_credential_is_denied(security, ids):
    issued = make_credential(
        security,
        ids,
        (APIScope.PROJECTS_READ,),
    )

    revoked = security.revoke(issued.credential)

    service = make_service(AllowAllAuthorization())

    with pytest.raises(DeveloperAuthorizationError, match="not active"):
        service.require(
            credential=revoked,
            secret=issued.secret,
            user_id=ids["user"],
            authentication_id=ids["auth"],
            tenant_id=ids["tenant"],
            resource=resource(ids),
            action=Action.READ,
        )


def test_expired_credential_is_denied(security, ids):
    issued = make_credential(
        security,
        ids,
        (APIScope.PROJECTS_READ,),
        expires_at=datetime.now(timezone.utc) + timedelta(seconds=1),
    )

    future = datetime.now(timezone.utc) + timedelta(seconds=2)

    service = make_service(AllowAllAuthorization())

    with pytest.raises(DeveloperAuthorizationError, match="expired"):
        service.require(
            credential=issued.credential,
            secret=issued.secret,
            user_id=ids["user"],
            authentication_id=ids["auth"],
            tenant_id=ids["tenant"],
            resource=resource(ids),
            action=Action.READ,
            now=future,
        )


def test_existing_authorization_deny_is_preserved(security, ids):
    issued = make_credential(
        security,
        ids,
        (APIScope.PROJECTS_READ,),
    )

    service = make_service(DenyAuthorization())

    with pytest.raises(
        DeveloperAuthorizationError,
        match="authorization denied",
    ):
        service.require(
            credential=issued.credential,
            secret=issued.secret,
            user_id=ids["user"],
            authentication_id=ids["auth"],
            tenant_id=ids["tenant"],
            resource=resource(ids),
            action=Action.READ,
        )


def test_decision_and_risk_scopes_are_mapped_independently():
    assert (
        DeveloperAuthorizationService.required_scope(
            ResourceType.DECISION,
            Action.READ,
        )
        is APIScope.DECISIONS_READ
    )

    assert (
        DeveloperAuthorizationService.required_scope(
            ResourceType.DECISION,
            Action.CREATE,
        )
        is APIScope.DECISIONS_WRITE
    )

    assert (
        DeveloperAuthorizationService.required_scope(
            ResourceType.RISK,
            Action.READ,
        )
        is APIScope.RISKS_READ
    )

    assert (
        DeveloperAuthorizationService.required_scope(
            ResourceType.RISK,
            Action.CREATE,
        )
        is APIScope.RISKS_WRITE
    )
