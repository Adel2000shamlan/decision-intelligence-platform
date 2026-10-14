import os
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import psycopg
import pytest

from app.modules.developer.domain.models import (
    APIScope,
    DeveloperApplication,
    DeveloperCredential,
    MarketplaceListing,
)
from app.modules.developer.persistence.postgres import (
    PostgresDeveloperRepository,
)


DATABASE_URL = os.getenv("DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not DATABASE_URL,
    reason="DATABASE_URL is not configured",
)


@pytest.fixture
def repository():
    with psycopg.connect(DATABASE_URL) as connection:
        repo = PostgresDeveloperRepository(connection)

        tenant_id = uuid4()

        try:
            yield repo, connection, tenant_id
        finally:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    DELETE FROM developer_applications
                    WHERE tenant_id = %s
                    """,
                    (tenant_id,),
                )
            connection.commit()


def make_application(tenant_id):
    return DeveloperApplication.create(
        tenant_id=tenant_id,
        name="Postgres Test Application",
    )


def make_credential(tenant_id, application_id, client_id="pg-client"):
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
        name="Postgres Listing",
        description="Postgres description",
        capability="projects",
    )


def test_application_crud(repository):
    repo, _, tenant_id = repository

    application = make_application(tenant_id)

    assert repo.save_application(application) == application
    assert repo.get_application(tenant_id, application.id) == application
    assert repo.list_applications(tenant_id) == (application,)

    repo.delete_application(tenant_id, application.id)

    assert repo.get_application(tenant_id, application.id) is None


def test_application_tenant_isolation(repository):
    repo, _, tenant_id = repository

    other_tenant = uuid4()
    application = make_application(tenant_id)

    repo.save_application(application)

    assert repo.get_application(
        other_tenant,
        application.id,
    ) is None


def test_credential_and_listing_crud(repository):
    repo, _, tenant_id = repository

    application = make_application(tenant_id)
    repo.save_application(application)

    credential = make_credential(
        tenant_id,
        application.id,
    )
    listing = make_listing(
        tenant_id,
        application.id,
    )

    assert repo.save_credential(credential) == credential
    assert repo.get_credential(
        tenant_id,
        credential.id,
    ) == credential

    assert repo.save_listing(listing) == listing
    assert repo.get_listing(
        tenant_id,
        listing.id,
    ) == listing


def test_cross_tenant_relationship_is_rejected(repository):
    repo, _, tenant_id = repository

    other_tenant = uuid4()

    application = make_application(tenant_id)
    repo.save_application(application)

    credential = make_credential(
        other_tenant,
        application.id,
        "cross-tenant",
    )

    with pytest.raises(Exception):
        repo.save_credential(credential)


def test_application_delete_cascades_children(repository):
    repo, _, tenant_id = repository

    application = make_application(tenant_id)
    repo.save_application(application)

    credential = make_credential(
        tenant_id,
        application.id,
        "cascade-client",
    )
    listing = make_listing(
        tenant_id,
        application.id,
    )

    repo.save_credential(credential)
    repo.save_listing(listing)

    repo.delete_application(
        tenant_id,
        application.id,
    )

    assert repo.get_credential(
        tenant_id,
        credential.id,
    ) is None

    assert repo.get_listing(
        tenant_id,
        listing.id,
    ) is None
