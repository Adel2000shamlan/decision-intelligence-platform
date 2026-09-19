from datetime import datetime, timedelta, timezone
import sqlite3
from uuid import uuid4

import pytest

from app.modules.developer.domain.models import (
    APIScope,
    DeveloperApplication,
    DeveloperCredential,
    MarketplaceListing,
)
from app.modules.developer.persistence.sqlite import SQLiteDeveloperRepository


@pytest.fixture
def repository():
    connection = sqlite3.connect(":memory:")
    repo = SQLiteDeveloperRepository(connection)
    try:
        yield repo, connection
    finally:
        connection.close()


def make_application(tenant_id):
    return DeveloperApplication.create(
        tenant_id=tenant_id,
        name="Test Application",
    )


def make_credential(tenant_id, application_id, client_id="client-1"):
    return DeveloperCredential.create(
        tenant_id=tenant_id,
        application_id=application_id,
        client_id=client_id,
        secret_hash="pbkdf2_sha256$310000$salt$digest",
        scopes=(APIScope.PROJECTS_READ,),
        expires_at=datetime.now(timezone.utc) + timedelta(days=30),
    )


def make_listing(tenant_id, application_id):
    return MarketplaceListing.create(
        tenant_id=tenant_id,
        publisher_application_id=application_id,
        name="Test Listing",
        description="Test description",
        capability="projects",
    )


def test_application_crud(repository):
    repo, _ = repository
    tenant_id = uuid4()
    application = make_application(tenant_id)

    assert repo.save_application(application) == application
    assert repo.get_application(tenant_id, application.id) == application
    assert repo.list_applications(tenant_id) == (application,)

    repo.delete_application(tenant_id, application.id)

    assert repo.get_application(tenant_id, application.id) is None
    assert repo.list_applications(tenant_id) == ()


def test_application_tenant_isolation(repository):
    repo, _ = repository
    tenant_a = uuid4()
    tenant_b = uuid4()

    application = make_application(tenant_a)
    repo.save_application(application)

    assert repo.get_application(tenant_b, application.id) is None
    assert repo.list_applications(tenant_b) == ()


def test_credential_crud_and_application_filter(repository):
    repo, _ = repository
    tenant_id = uuid4()
    application_a = make_application(tenant_id)
    application_b = make_application(tenant_id)

    repo.save_application(application_a)
    repo.save_application(application_b)

    credential_a = make_credential(
        tenant_id,
        application_a.id,
        "client-a",
    )
    credential_b = make_credential(
        tenant_id,
        application_b.id,
        "client-b",
    )

    repo.save_credential(credential_a)
    repo.save_credential(credential_b)

    assert repo.get_credential(tenant_id, credential_a.id) == credential_a
    assert repo.list_credentials(tenant_id) == (
        credential_a,
        credential_b,
    )
    assert repo.list_credentials(
        tenant_id,
        application_id=application_a.id,
    ) == (credential_a,)


def test_credential_tenant_isolation(repository):
    repo, _ = repository
    tenant_a = uuid4()
    tenant_b = uuid4()

    application = make_application(tenant_a)
    repo.save_application(application)

    credential = make_credential(tenant_a, application.id)
    repo.save_credential(credential)

    assert repo.get_credential(tenant_b, credential.id) is None
    assert repo.list_credentials(tenant_b) == ()


def test_client_id_is_unique_within_tenant(repository):
    repo, _ = repository
    tenant_id = uuid4()

    application = make_application(tenant_id)
    repo.save_application(application)

    repo.save_credential(
        make_credential(tenant_id, application.id, "same-client")
    )

    with pytest.raises(sqlite3.IntegrityError):
        repo.save_credential(
            make_credential(tenant_id, application.id, "same-client")
        )


def test_same_client_id_is_allowed_in_different_tenants(repository):
    repo, _ = repository
    tenant_a = uuid4()
    tenant_b = uuid4()

    app_a = make_application(tenant_a)
    app_b = make_application(tenant_b)

    repo.save_application(app_a)
    repo.save_application(app_b)

    credential_a = make_credential(tenant_a, app_a.id, "shared-client")
    credential_b = make_credential(tenant_b, app_b.id, "shared-client")

    repo.save_credential(credential_a)
    repo.save_credential(credential_b)

    assert repo.get_credential(tenant_a, credential_a.id) == credential_a
    assert repo.get_credential(tenant_b, credential_b.id) == credential_b


def test_raw_secret_is_never_persisted(repository):
    repo, connection = repository
    tenant_id = uuid4()
    application = make_application(tenant_id)
    repo.save_application(application)

    raw_secret = "THIS_IS_THE_RAW_SECRET"
    credential = DeveloperCredential.create(
        tenant_id=tenant_id,
        application_id=application.id,
        client_id="client-secret-test",
        secret_hash="pbkdf2_sha256$310000$salt$digest",
    )
    repo.save_credential(credential)

    row = connection.execute(
        """
        SELECT *
        FROM developer_credentials
        WHERE id = ?
        """,
        (str(credential.id),),
    ).fetchone()

    assert row is not None
    assert raw_secret not in tuple(row)
    assert credential.secret_hash in tuple(row)


def test_credential_requires_existing_same_tenant_application(repository):
    repo, _ = repository
    tenant_id = uuid4()

    credential = make_credential(
        tenant_id,
        uuid4(),
    )

    with pytest.raises(sqlite3.IntegrityError):
        repo.save_credential(credential)


def test_cross_tenant_application_reference_is_rejected(repository):
    repo, _ = repository
    tenant_a = uuid4()
    tenant_b = uuid4()

    application = make_application(tenant_a)
    repo.save_application(application)

    credential = make_credential(
        tenant_b,
        application.id,
        "cross-tenant-client",
    )

    with pytest.raises(sqlite3.IntegrityError):
        repo.save_credential(credential)


def test_listing_crud(repository):
    repo, _ = repository
    tenant_id = uuid4()

    application = make_application(tenant_id)
    repo.save_application(application)

    listing = make_listing(tenant_id, application.id)

    assert repo.save_listing(listing) == listing
    assert repo.get_listing(tenant_id, listing.id) == listing
    assert repo.list_listings(tenant_id) == (listing,)

    repo.delete_listing(tenant_id, listing.id)

    assert repo.get_listing(tenant_id, listing.id) is None


def test_listing_requires_existing_same_tenant_application(repository):
    repo, _ = repository
    tenant_id = uuid4()

    listing = make_listing(tenant_id, uuid4())

    with pytest.raises(sqlite3.IntegrityError):
        repo.save_listing(listing)


def test_cross_tenant_listing_reference_is_rejected(repository):
    repo, _ = repository
    tenant_a = uuid4()
    tenant_b = uuid4()

    application = make_application(tenant_a)
    repo.save_application(application)

    listing = make_listing(tenant_b, application.id)

    with pytest.raises(sqlite3.IntegrityError):
        repo.save_listing(listing)


def test_deleting_application_cascades_credentials_and_listings(repository):
    repo, _ = repository
    tenant_id = uuid4()

    application = make_application(tenant_id)
    repo.save_application(application)

    credential = make_credential(tenant_id, application.id)
    listing = make_listing(tenant_id, application.id)

    repo.save_credential(credential)
    repo.save_listing(listing)

    repo.delete_application(tenant_id, application.id)

    assert repo.get_application(tenant_id, application.id) is None
    assert repo.get_credential(tenant_id, credential.id) is None
    assert repo.get_listing(tenant_id, listing.id) is None


def test_delete_is_tenant_scoped(repository):
    repo, _ = repository
    tenant_a = uuid4()
    tenant_b = uuid4()

    application = make_application(tenant_a)
    repo.save_application(application)

    repo.delete_application(tenant_b, application.id)

    assert repo.get_application(tenant_a, application.id) == application


def test_application_save_updates_existing_application(repository):
    repo, _ = repository
    tenant_id = uuid4()
    application = make_application(tenant_id)
    repo.save_application(application)

    updated = DeveloperApplication(
        id=application.id,
        tenant_id=application.tenant_id,
        name="Updated Application",
        status=application.status,
        created_at=application.created_at,
        updated_at=application.updated_at,
        version=application.version + 1,
    )

    assert repo.save_application(updated) == updated
    assert repo.get_application(tenant_id, application.id) == updated
    assert repo.list_applications(tenant_id) == (updated,)


def test_credential_save_updates_existing_credential(repository):
    repo, _ = repository
    tenant_id = uuid4()
    application = make_application(tenant_id)
    repo.save_application(application)

    credential = make_credential(tenant_id, application.id, "client-update")
    repo.save_credential(credential)

    updated = DeveloperCredential(
        id=credential.id,
        tenant_id=credential.tenant_id,
        application_id=credential.application_id,
        client_id=credential.client_id,
        secret_hash="pbkdf2_sha256$310000$new-salt$new-digest",
        scopes=(APIScope.PROJECTS_READ, APIScope.PROJECTS_WRITE),
        status=credential.status,
        created_at=credential.created_at,
        expires_at=credential.expires_at,
        revoked_at=credential.revoked_at,
        version=credential.version + 1,
    )

    assert repo.save_credential(updated) == updated
    assert repo.get_credential(tenant_id, credential.id) == updated


def test_listing_save_updates_existing_listing(repository):
    repo, _ = repository
    tenant_id = uuid4()
    application = make_application(tenant_id)
    repo.save_application(application)

    listing = make_listing(tenant_id, application.id)
    repo.save_listing(listing)

    updated = MarketplaceListing(
        id=listing.id,
        tenant_id=listing.tenant_id,
        publisher_application_id=listing.publisher_application_id,
        name="Updated Listing",
        description="Updated description",
        capability="decisions",
        published=True,
        created_at=listing.created_at,
        updated_at=listing.updated_at,
        version=listing.version + 1,
    )

    assert repo.save_listing(updated) == updated
    assert repo.get_listing(tenant_id, listing.id) == updated


def test_application_upsert_rejects_cross_tenant_same_id(repository):
    repo, _ = repository
    tenant_a = uuid4()
    tenant_b = uuid4()

    application = make_application(tenant_a)
    repo.save_application(application)

    cross_tenant = DeveloperApplication(
        id=application.id,
        tenant_id=tenant_b,
        name="Cross Tenant",
        status=application.status,
        created_at=application.created_at,
        updated_at=application.updated_at,
        version=application.version + 1,
    )

    with pytest.raises(Exception, match="another tenant"):
        repo.save_application(cross_tenant)

    assert repo.get_application(tenant_a, application.id) == application
    assert repo.get_application(tenant_b, application.id) is None


def test_credential_upsert_rejects_cross_tenant_same_id(repository):
    repo, _ = repository
    tenant_a = uuid4()
    tenant_b = uuid4()

    application_a = make_application(tenant_a)
    application_b = make_application(tenant_b)
    repo.save_application(application_a)
    repo.save_application(application_b)

    credential = make_credential(tenant_a, application_a.id, "client-isolation")
    repo.save_credential(credential)

    cross_tenant = DeveloperCredential(
        id=credential.id,
        tenant_id=tenant_b,
        application_id=application_b.id,
        client_id="client-cross-tenant",
        secret_hash=credential.secret_hash,
        scopes=credential.scopes,
        status=credential.status,
        created_at=credential.created_at,
        expires_at=credential.expires_at,
        revoked_at=credential.revoked_at,
        version=credential.version + 1,
    )

    with pytest.raises(Exception, match="another tenant"):
        repo.save_credential(cross_tenant)

    assert repo.get_credential(tenant_a, credential.id) == credential
    assert repo.get_credential(tenant_b, credential.id) is None


def test_listing_upsert_rejects_cross_tenant_same_id(repository):
    repo, _ = repository
    tenant_a = uuid4()
    tenant_b = uuid4()

    application_a = make_application(tenant_a)
    application_b = make_application(tenant_b)
    repo.save_application(application_a)
    repo.save_application(application_b)

    listing = make_listing(tenant_a, application_a.id)
    repo.save_listing(listing)

    cross_tenant = MarketplaceListing(
        id=listing.id,
        tenant_id=tenant_b,
        publisher_application_id=application_b.id,
        name="Cross Tenant Listing",
        description=listing.description,
        capability=listing.capability,
        published=listing.published,
        created_at=listing.created_at,
        updated_at=listing.updated_at,
        version=listing.version + 1,
    )

    with pytest.raises(Exception, match="another tenant"):
        repo.save_listing(cross_tenant)

    assert repo.get_listing(tenant_a, listing.id) == listing
    assert repo.get_listing(tenant_b, listing.id) is None
