import sqlite3
from uuid import uuid4

import pytest

from app.modules.developer.application.service import DeveloperService
from app.modules.developer.domain.models import (
    APIScope,
    DeveloperApplicationStatus,
    DeveloperCredentialStatus,
)
from app.modules.developer.persistence.sqlite import SQLiteDeveloperRepository
from app.shared.domain.errors import BusinessRuleViolation


def make_service() -> DeveloperService:
    import sqlite3

    connection = sqlite3.connect(":memory:")
    repository = SQLiteDeveloperRepository(connection)
    return DeveloperService(repository=repository)


def test_create_application_and_list_tenant_scoped():
    service = make_service()
    tenant_id = uuid4()

    application = service.create_application(
        tenant_id=tenant_id,
        name="Decision Client",
    )

    assert application.tenant_id == tenant_id
    assert application.name == "Decision Client"
    assert service.get_application(
        tenant_id=tenant_id,
        application_id=application.id,
    ) == application
    assert service.list_applications(tenant_id) == (application,)

    other_tenant = uuid4()
    assert service.list_applications(other_tenant) == ()
    assert service.get_application(
        tenant_id=other_tenant,
        application_id=application.id,
    ) is None


def test_issue_credential_returns_raw_secret_once_and_persists_only_hash():
    service = make_service()
    tenant_id = uuid4()

    application = service.create_application(
        tenant_id=tenant_id,
        name="API Client",
    )

    issued = service.issue_credential(
        tenant_id=tenant_id,
        application_id=application.id,
        client_id="client-001",
        scopes=(APIScope.PROJECTS_READ,),
    )

    assert issued.secret
    assert issued.secret != issued.credential.secret_hash
    assert service.verify_credential(
        tenant_id=tenant_id,
        credential_id=issued.credential.id,
        secret=issued.secret,
    ) is True

    stored = service.get_credential(
        tenant_id=tenant_id,
        credential_id=issued.credential.id,
    )
    assert stored is not None
    assert issued.secret not in stored.secret_hash


def test_issue_credential_requires_existing_same_tenant_application():
    service = make_service()

    with pytest.raises(BusinessRuleViolation, match="application not found"):
        service.issue_credential(
            tenant_id=uuid4(),
            application_id=uuid4(),
            client_id="client-001",
        )


def test_issue_credential_rejects_cross_tenant_application():
    service = make_service()

    owner_tenant = uuid4()
    other_tenant = uuid4()

    application = service.create_application(
        tenant_id=owner_tenant,
        name="Owner Application",
    )

    with pytest.raises(BusinessRuleViolation, match="application not found"):
        service.issue_credential(
            tenant_id=other_tenant,
            application_id=application.id,
            client_id="client-001",
        )


@pytest.mark.parametrize(
    "status",
    [
        DeveloperApplicationStatus.SUSPENDED,
        DeveloperApplicationStatus.ARCHIVED,
    ],
)
def test_issue_credential_rejects_inactive_application(status):
    service = make_service()
    tenant_id = uuid4()

    application = service.create_application(
        tenant_id=tenant_id,
        name="Lifecycle Application",
    )
    application = service.set_application_status(
        tenant_id=tenant_id,
        application_id=application.id,
        status=status,
    )

    with pytest.raises(
        BusinessRuleViolation,
        match="application is not active",
    ):
        service.issue_credential(
            tenant_id=tenant_id,
            application_id=application.id,
            client_id="client-001",
        )


def test_revoke_credential_changes_status():
    service = make_service()
    tenant_id = uuid4()

    application = service.create_application(
        tenant_id=tenant_id,
        name="Revoke Client",
    )
    issued = service.issue_credential(
        tenant_id=tenant_id,
        application_id=application.id,
        client_id="client-001",
    )

    revoked = service.revoke_credential(
        tenant_id=tenant_id,
        credential_id=issued.credential.id,
    )

    assert revoked.status is DeveloperCredentialStatus.REVOKED
    assert revoked.version == issued.credential.version + 1
    assert service.verify_credential(
        tenant_id=tenant_id,
        credential_id=issued.credential.id,
        secret=issued.secret,
    ) is False


def test_rotate_credential_changes_secret_and_preserves_identity():
    service = make_service()
    tenant_id = uuid4()

    application = service.create_application(
        tenant_id=tenant_id,
        name="Rotation Client",
    )
    issued = service.issue_credential(
        tenant_id=tenant_id,
        application_id=application.id,
        client_id="client-001",
    )

    rotated = service.rotate_credential(
        tenant_id=tenant_id,
        credential_id=issued.credential.id,
    )

    assert rotated.credential.id == issued.credential.id
    assert rotated.secret != issued.secret
    assert rotated.credential.secret_hash != issued.credential.secret_hash
    assert rotated.credential.version == issued.credential.version + 1

    assert service.verify_credential(
        tenant_id=tenant_id,
        credential_id=issued.credential.id,
        secret=issued.secret,
    ) is False

    assert service.verify_credential(
        tenant_id=tenant_id,
        credential_id=issued.credential.id,
        secret=rotated.secret,
    ) is True


def test_rotate_rejects_revoked_credential():
    service = make_service()
    tenant_id = uuid4()

    application = service.create_application(
        tenant_id=tenant_id,
        name="Rotation Client",
    )
    issued = service.issue_credential(
        tenant_id=tenant_id,
        application_id=application.id,
        client_id="client-001",
    )

    service.revoke_credential(
        tenant_id=tenant_id,
        credential_id=issued.credential.id,
    )

    with pytest.raises(
        BusinessRuleViolation,
        match="only active credentials can be rotated",
    ):
        service.rotate_credential(
            tenant_id=tenant_id,
            credential_id=issued.credential.id,
        )


def test_create_listing_requires_same_tenant_application():
    service = make_service()
    tenant_id = uuid4()

    application = service.create_application(
        tenant_id=tenant_id,
        name="Publisher",
    )

    listing = service.create_listing(
        tenant_id=tenant_id,
        publisher_application_id=application.id,
        name="Decision API",
        description="Decision intelligence capability",
        capability="decision-analysis",
    )

    assert listing.published is False
    assert service.get_listing(
        tenant_id=tenant_id,
        listing_id=listing.id,
    ) == listing


def test_create_listing_rejects_cross_tenant_application():
    service = make_service()

    owner_tenant = uuid4()
    other_tenant = uuid4()

    application = service.create_application(
        tenant_id=owner_tenant,
        name="Publisher",
    )

    with pytest.raises(BusinessRuleViolation, match="application not found"):
        service.create_listing(
            tenant_id=other_tenant,
            publisher_application_id=application.id,
            name="Cross Tenant Listing",
            description="Should fail",
            capability="test",
        )


def test_publish_and_unpublish_listing():
    service = make_service()
    tenant_id = uuid4()

    application = service.create_application(
        tenant_id=tenant_id,
        name="Publisher",
    )

    listing = service.create_listing(
        tenant_id=tenant_id,
        publisher_application_id=application.id,
        name="Capability",
        description="Capability description",
        capability="test",
    )

    published = service.publish_listing(
        tenant_id=tenant_id,
        listing_id=listing.id,
    )

    assert published.published is True
    assert published.version == listing.version + 1

    unpublished = service.unpublish_listing(
        tenant_id=tenant_id,
        listing_id=listing.id,
    )

    assert unpublished.published is False
    assert unpublished.version == published.version + 1


def test_read_operations_are_tenant_scoped():
    service = make_service()
    tenant_id = uuid4()
    other_tenant = uuid4()

    application = service.create_application(
        tenant_id=tenant_id,
        name="Private Application",
    )

    issued = service.issue_credential(
        tenant_id=tenant_id,
        application_id=application.id,
        client_id="client-private",
    )

    listing = service.create_listing(
        tenant_id=tenant_id,
        publisher_application_id=application.id,
        name="Private Listing",
        description="Private",
        capability="private",
    )

    assert service.get_application(
        tenant_id=other_tenant,
        application_id=application.id,
    ) is None

    assert service.get_credential(
        tenant_id=other_tenant,
        credential_id=issued.credential.id,
    ) is None

    assert service.get_listing(
        tenant_id=other_tenant,
        listing_id=listing.id,
    ) is None

    assert service.list_credentials(other_tenant) == ()
    assert service.list_listings(other_tenant) == ()


def test_remove_application_cascades_marketplace_listings():
    tenant_id = uuid4()

    repository = SQLiteDeveloperRepository(sqlite3.connect(":memory:"))
    service = DeveloperService(repository)

    application = service.create_application(
        tenant_id=tenant_id,
        name="Cascade Test App",
    )

    listing = service.create_listing(
        tenant_id=tenant_id,
        publisher_application_id=application.id,
        name="Cascade Listing",
        description="Must disappear with publisher application",
        capability="decision-analysis",
    )

    assert service.get_listing(
        tenant_id=tenant_id,
        listing_id=listing.id,
    ) is not None

    service.remove_application(
        tenant_id=tenant_id,
        application_id=application.id,
    )

    assert service.get_application(
        tenant_id=tenant_id,
        application_id=application.id,
    ) is None

    assert service.get_listing(
        tenant_id=tenant_id,
        listing_id=listing.id,
    ) is None
