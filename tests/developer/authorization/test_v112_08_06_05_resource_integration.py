from uuid import uuid4

import pytest

from app.modules.authorization.domain.models import (
    Action,
    ExplicitPermissionPolicy,
    Resource,
    ResourceType,
)
from app.modules.authorization.domain.resource_authorization import (
    ResourceRecord,
    ResourceStatus,
)
from app.modules.developer.authorization.adapter import (
    DeveloperAuthorizationError,
    DeveloperAuthorizationService,
)
from app.modules.developer.domain.models import APIScope
from app.modules.developer.security.credentials import (
    DeveloperCredentialSecurityService,
)


class RecordingResolver:
    def __init__(self, record=None):
        self.record = record
        self.calls = []

    def resolve(self, resource):
        self.calls.append(resource)
        return self.record


def test_developer_authorization_uses_injected_resource_resolver():
    security = DeveloperCredentialSecurityService()

    tenant_id = uuid4()
    application_id = uuid4()
    user_id = uuid4()
    authentication_id = uuid4()
    resource_id = uuid4()

    issued = security.issue(
        tenant_id=tenant_id,
        application_id=application_id,
        client_id=f"client-{uuid4()}",
        scopes=(APIScope.PROJECTS_READ,),
    )

    resource = Resource(
        ResourceType.PROJECT,
        resource_id,
        tenant_id,
    )

    resolver = RecordingResolver(
        ResourceRecord(
            resource=resource,
            owner_id=None,
            status=ResourceStatus.ACTIVE,
            exists=True,
        )
    )

    service = DeveloperAuthorizationService.create(
        resource_resolver=resolver,
        policies=(
            ExplicitPermissionPolicy(
                frozenset({"project:read"}),
            ),
        ),
    )

    decision = service.require(
        credential=issued.credential,
        secret=issued.secret,
        user_id=user_id,
        authentication_id=authentication_id,
        tenant_id=tenant_id,
        resource=resource,
        action=Action.READ,
    )

    assert decision.allowed is True
    assert len(resolver.calls) == 1
    assert resolver.calls[0] == resource


def test_developer_authorization_fails_when_resource_resolver_returns_none():
    security = DeveloperCredentialSecurityService()

    tenant_id = uuid4()
    application_id = uuid4()
    user_id = uuid4()
    authentication_id = uuid4()

    issued = security.issue(
        tenant_id=tenant_id,
        application_id=application_id,
        client_id=f"client-{uuid4()}",
        scopes=(APIScope.PROJECTS_READ,),
    )

    resource = Resource(
        ResourceType.PROJECT,
        uuid4(),
        tenant_id,
    )

    resolver = RecordingResolver(record=None)

    service = DeveloperAuthorizationService.create(
        resource_resolver=resolver,
    )

    with pytest.raises(
        DeveloperAuthorizationError,
        match="protected resource was not found",
    ):
        service.require(
            credential=issued.credential,
            secret=issued.secret,
            user_id=user_id,
            authentication_id=authentication_id,
            tenant_id=tenant_id,
            resource=resource,
            action=Action.READ,
        )

    assert len(resolver.calls) == 1
    assert resolver.calls[0] == resource


def test_developer_authorization_rejects_archived_resource():
    security = DeveloperCredentialSecurityService()

    tenant_id = uuid4()
    application_id = uuid4()
    user_id = uuid4()
    authentication_id = uuid4()

    issued = security.issue(
        tenant_id=tenant_id,
        application_id=application_id,
        client_id=f"client-{uuid4()}",
        scopes=(APIScope.PROJECTS_READ,),
    )

    resource = Resource(
        ResourceType.PROJECT,
        uuid4(),
        tenant_id,
    )

    resolver = RecordingResolver(
        ResourceRecord(
            resource=resource,
            owner_id=None,
            status=ResourceStatus.ARCHIVED,
            exists=True,
        )
    )

    service = DeveloperAuthorizationService.create(
        resource_resolver=resolver,
    )

    with pytest.raises(
        DeveloperAuthorizationError,
        match="resource is unavailable",
    ):
        service.require(
            credential=issued.credential,
            secret=issued.secret,
            user_id=user_id,
            authentication_id=authentication_id,
            tenant_id=tenant_id,
            resource=resource,
            action=Action.READ,
        )
