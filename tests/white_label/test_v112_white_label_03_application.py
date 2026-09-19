from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from app.modules.authorization.domain.models import AuthorizationContext
from app.modules.organization.domain.models import Organization
from app.modules.white_label.application.service import (
    WhiteLabelApplicationService,
)
from app.modules.white_label.domain.models import (
    DEFAULT_DISPLAY_NAME,
    WhiteLabelConfiguration,
)
from app.modules.white_label.persistence.sqlite import (
    SQLiteWhiteLabelRepository,
)
from app.shared.domain.errors import BusinessRuleViolation, EntityNotFound


class RecordingAuthorization:
    def __init__(self):
        self.calls = []

    def require(self, context: AuthorizationContext):
        self.calls.append(
            {
                "action": context.permission.action.value,
                "actor_id": context.actor.actor_id,
                "tenant_id": context.tenant_id,
                "resource_id": context.resource.resource_id,
                "authentication_id": context.actor.authentication_id,
            }
        )


class FakeOrganizationRepository:
    def __init__(self):
        self.items = {}
        self.tenant_ids = {}

    def get_by_id(self, organization_id):
        return self.items.get(organization_id)

    def get_tenant_id(self, organization_id):
        return self.tenant_ids.get(organization_id)

    def add(self, organization, *, tenant_id):
        self.items[organization.id] = organization
        self.tenant_ids[organization.id] = tenant_id


@pytest.fixture
def repository():
    import sqlite3

    connection = sqlite3.connect(":memory:")
    connection.execute(
        """
        CREATE TABLE white_label_configurations (
            id TEXT PRIMARY KEY,
            tenant_id TEXT NOT NULL,
            organization_id TEXT NULL,
            display_name TEXT NOT NULL,
            short_name TEXT NOT NULL,
            description TEXT NOT NULL,
            logo_url TEXT NULL,
            favicon_url TEXT NULL,
            primary_color TEXT NOT NULL,
            secondary_color TEXT NOT NULL,
            background_color TEXT NOT NULL,
            theme_color TEXT NOT NULL,
            locale TEXT NOT NULL,
            direction TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            version INTEGER NOT NULL,
            UNIQUE(tenant_id)
        )
        """
    )
    connection.commit()

    yield SQLiteWhiteLabelRepository(connection)

    connection.close()


@pytest.fixture
def organization_repository():
    return FakeOrganizationRepository()


@pytest.fixture
def authorization():
    return RecordingAuthorization()


@pytest.fixture
def service(repository, organization_repository, authorization):
    return WhiteLabelApplicationService(
        repository=repository,
        organization_repository=organization_repository,
        authorization=authorization,
    )


def make_organization():
    now = datetime.now(timezone.utc)
    return Organization(
        id=uuid4(),
        name="Test Organization",
        slug=f"org-{uuid4().hex[:8]}",
        created_at=now,
        updated_at=now,
        version=1,
    )


def test_get_returns_ephemeral_defaults_without_persisting(
    service,
    repository,
):
    tenant_id = uuid4()

    result = service.get(
        tenant_id=tenant_id,
        actor_id=uuid4(),
        authentication_id=uuid4(),
    )

    assert result.tenant_id == tenant_id
    assert result.display_name == DEFAULT_DISPLAY_NAME
    assert repository.get_by_tenant(tenant_id) is None


def test_get_returns_persisted_configuration_for_same_tenant(
    service,
    repository,
):
    tenant_id = uuid4()

    created = service.create(
        tenant_id=tenant_id,
        actor_id=uuid4(),
        authentication_id=uuid4(),
        display_name="Custom Brand",
    )

    result = service.get(
        tenant_id=tenant_id,
        actor_id=uuid4(),
        authentication_id=uuid4(),
    )

    assert result.id == created.id
    assert result.display_name == "Custom Brand"


def test_get_by_id_allows_same_tenant(
    service,
):
    tenant_id = uuid4()

    created = service.create(
        tenant_id=tenant_id,
        actor_id=uuid4(),
        authentication_id=uuid4(),
    )

    result = service.get_by_id(
        tenant_id=tenant_id,
        configuration_id=created.id,
        actor_id=uuid4(),
        authentication_id=uuid4(),
    )

    assert result.id == created.id


def test_get_by_id_rejects_cross_tenant_access(
    service,
):
    tenant_a = uuid4()
    tenant_b = uuid4()

    created = service.create(
        tenant_id=tenant_a,
        actor_id=uuid4(),
        authentication_id=uuid4(),
    )

    with pytest.raises(
        BusinessRuleViolation,
        match="tenant mismatch",
    ):
        service.get_by_id(
            tenant_id=tenant_b,
            configuration_id=created.id,
            actor_id=uuid4(),
            authentication_id=uuid4(),
        )


def test_create_rejects_duplicate_tenant(
    service,
):
    tenant_id = uuid4()

    service.create(
        tenant_id=tenant_id,
        actor_id=uuid4(),
        authentication_id=uuid4(),
    )

    with pytest.raises(
        BusinessRuleViolation,
        match="already exists",
    ):
        service.create(
            tenant_id=tenant_id,
            actor_id=uuid4(),
            authentication_id=uuid4(),
        )


def test_create_requires_organization_repository_when_organization_is_supplied(
    repository,
    authorization,
):
    service = WhiteLabelApplicationService(
        repository=repository,
        authorization=authorization,
    )

    with pytest.raises(
        BusinessRuleViolation,
        match="organization repository is required",
    ):
        service.create(
            tenant_id=uuid4(),
            actor_id=uuid4(),
            authentication_id=uuid4(),
            organization_id=uuid4(),
        )


def test_create_accepts_organization_owned_by_same_tenant(
    service,
    organization_repository,
):
    tenant_id = uuid4()
    organization = make_organization()
    organization_repository.add(
        organization,
        tenant_id=tenant_id,
    )

    result = service.create(
        tenant_id=tenant_id,
        actor_id=uuid4(),
        authentication_id=uuid4(),
        organization_id=organization.id,
    )

    assert result.organization_id == organization.id


def test_create_rejects_organization_owned_by_other_tenant(
    service,
    organization_repository,
):
    tenant_id = uuid4()
    other_tenant_id = uuid4()

    organization = make_organization()
    organization_repository.add(
        organization,
        tenant_id=other_tenant_id,
    )

    with pytest.raises(
        BusinessRuleViolation,
        match="tenant mismatch",
    ):
        service.create(
            tenant_id=tenant_id,
            actor_id=uuid4(),
            authentication_id=uuid4(),
            organization_id=organization.id,
        )


def test_create_rejects_missing_organization(
    service,
):
    with pytest.raises(EntityNotFound, match="organization not found"):
        service.create(
            tenant_id=uuid4(),
            actor_id=uuid4(),
            authentication_id=uuid4(),
            organization_id=uuid4(),
        )


def test_update_increments_version_and_updates_timestamp(
    service,
):
    tenant_id = uuid4()

    created = service.create(
        tenant_id=tenant_id,
        actor_id=uuid4(),
        authentication_id=uuid4(),
        display_name="Before",
    )

    updated = service.update(
        tenant_id=tenant_id,
        configuration_id=created.id,
        actor_id=uuid4(),
        authentication_id=uuid4(),
        display_name="After",
    )

    assert updated.id == created.id
    assert updated.version == created.version + 1
    assert updated.display_name == "After"
    assert updated.updated_at > created.updated_at


def test_update_rejects_cross_tenant_access(
    service,
):
    tenant_a = uuid4()
    tenant_b = uuid4()

    created = service.create(
        tenant_id=tenant_a,
        actor_id=uuid4(),
        authentication_id=uuid4(),
    )

    with pytest.raises(
        BusinessRuleViolation,
        match="tenant mismatch",
    ):
        service.update(
            tenant_id=tenant_b,
            configuration_id=created.id,
            actor_id=uuid4(),
            authentication_id=uuid4(),
            display_name="Attack",
        )

    stored = service.get(
        tenant_id=tenant_a,
        actor_id=uuid4(),
        authentication_id=uuid4(),
    )

    assert stored.display_name == DEFAULT_DISPLAY_NAME


def test_update_validates_new_organization(
    service,
    organization_repository,
):
    tenant_id = uuid4()
    created = service.create(
        tenant_id=tenant_id,
        actor_id=uuid4(),
        authentication_id=uuid4(),
    )

    other_tenant_org = make_organization()
    organization_repository.add(
        other_tenant_org,
        tenant_id=uuid4(),
    )

    with pytest.raises(
        BusinessRuleViolation,
        match="tenant mismatch",
    ):
        service.update(
            tenant_id=tenant_id,
            configuration_id=created.id,
            actor_id=uuid4(),
            authentication_id=uuid4(),
            organization_id=other_tenant_org.id,
        )


def test_delete_removes_owned_configuration(
    service,
    repository,
):
    tenant_id = uuid4()

    created = service.create(
        tenant_id=tenant_id,
        actor_id=uuid4(),
        authentication_id=uuid4(),
    )

    service.delete(
        tenant_id=tenant_id,
        configuration_id=created.id,
        actor_id=uuid4(),
        authentication_id=uuid4(),
    )

    assert repository.get_by_id(created.id) is None


def test_delete_rejects_cross_tenant_access_and_preserves_configuration(
    service,
):
    tenant_a = uuid4()
    tenant_b = uuid4()

    created = service.create(
        tenant_id=tenant_a,
        actor_id=uuid4(),
        authentication_id=uuid4(),
    )

    with pytest.raises(
        BusinessRuleViolation,
        match="tenant mismatch",
    ):
        service.delete(
            tenant_id=tenant_b,
            configuration_id=created.id,
            actor_id=uuid4(),
            authentication_id=uuid4(),
        )

    assert service.get_by_id(
        tenant_id=tenant_a,
        configuration_id=created.id,
        actor_id=uuid4(),
        authentication_id=uuid4(),
    ).id == created.id


@pytest.mark.parametrize(
    "method",
    ["get", "create"],
)
def test_invalid_tenant_is_rejected(
    service,
    method,
):
    with pytest.raises(
        BusinessRuleViolation,
        match="tenant_id must be a UUID",
    ):
        getattr(service, method)(
            tenant_id="not-a-uuid",
            actor_id=uuid4(),
            authentication_id=uuid4(),
        )


def test_authorization_is_called_once_per_public_operation(
    service,
    authorization,
):
    tenant_id = uuid4()
    actor_id = uuid4()
    authentication_id = uuid4()

    created = service.create(
        tenant_id=tenant_id,
        actor_id=actor_id,
        authentication_id=authentication_id,
    )

    assert [call["action"] for call in authorization.calls] == [
        "create",
    ]

    authorization.calls.clear()

    service.get_by_id(
        tenant_id=tenant_id,
        configuration_id=created.id,
        actor_id=actor_id,
        authentication_id=authentication_id,
    )

    assert [call["action"] for call in authorization.calls] == [
        "read",
    ]

    authorization.calls.clear()

    service.update(
        tenant_id=tenant_id,
        configuration_id=created.id,
        actor_id=actor_id,
        authentication_id=authentication_id,
    )

    assert [call["action"] for call in authorization.calls] == [
        "update",
    ]

    authorization.calls.clear()

    service.delete(
        tenant_id=tenant_id,
        configuration_id=created.id,
        actor_id=actor_id,
        authentication_id=authentication_id,
    )

    assert [call["action"] for call in authorization.calls] == [
        "delete",
    ]
