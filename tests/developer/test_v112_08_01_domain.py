from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from app.modules.developer.domain.models import (
    APIScope,
    DeveloperApplication,
    DeveloperCredential,
    DeveloperCredentialStatus,
    MarketplaceListing,
)
from app.shared.domain.errors import InvalidDomainData


def test_developer_application_requires_tenant_and_name():
    tenant_id = uuid4()

    application = DeveloperApplication.create(
        tenant_id=tenant_id,
        name="  My Developer App  ",
    )

    assert application.tenant_id == tenant_id
    assert application.name == "My Developer App"


def test_developer_application_rejects_empty_name():
    with pytest.raises(InvalidDomainData):
        DeveloperApplication.create(
            tenant_id=uuid4(),
            name="   ",
        )


def test_credential_normalizes_and_deduplicates_scopes():
    credential = DeveloperCredential.create(
        tenant_id=uuid4(),
        application_id=uuid4(),
        client_id="client-001",
        secret_hash="hashed-secret",
        scopes=[
            APIScope.PROJECTS_READ,
            APIScope.PROJECTS_READ,
            "risks:read",
        ],
    )

    assert credential.scopes == (
        APIScope.PROJECTS_READ,
        APIScope.RISKS_READ,
    )
    assert credential.has_scope("projects:read")
    assert not credential.has_scope("projects:write")


def test_credential_rejects_missing_secret_hash():
    with pytest.raises(InvalidDomainData):
        DeveloperCredential.create(
            tenant_id=uuid4(),
            application_id=uuid4(),
            client_id="client-001",
            secret_hash="",
        )


def test_credential_rejects_secret_hash_equal_to_client_id():
    with pytest.raises(InvalidDomainData):
        DeveloperCredential.create(
            tenant_id=uuid4(),
            application_id=uuid4(),
            client_id="same-value",
            secret_hash="same-value",
        )


def test_credential_expiry_is_detected():
    credential = DeveloperCredential.create(
        tenant_id=uuid4(),
        application_id=uuid4(),
        client_id="client-001",
        secret_hash="hashed-secret",
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )

    assert not credential.is_expired(
        datetime.now(timezone.utc)
    )

    assert credential.is_expired(
        credential.expires_at + timedelta(seconds=1)
    )


def test_credential_revoke_is_terminal_for_status():
    credential = DeveloperCredential.create(
        tenant_id=uuid4(),
        application_id=uuid4(),
        client_id="client-001",
        secret_hash="hashed-secret",
    )

    revoked = credential.revoke()

    assert revoked.status is DeveloperCredentialStatus.REVOKED
    assert revoked.revoked_at is not None
    assert revoked.version == credential.version + 1


def test_marketplace_listing_starts_unpublished():
    listing = MarketplaceListing.create(
        tenant_id=uuid4(),
        publisher_application_id=uuid4(),
        name="Decision Intelligence",
        description="Decision capability",
        capability="decision-analysis",
    )

    assert listing.published is False

    published = listing.publish()

    assert published.published is True
    assert published.version == listing.version + 1


def test_marketplace_listing_can_be_unpublished():
    listing = MarketplaceListing.create(
        tenant_id=uuid4(),
        publisher_application_id=uuid4(),
        name="Decision Intelligence",
        description="Decision capability",
        capability="decision-analysis",
    ).publish()

    unpublished = listing.unpublish()

    assert unpublished.published is False
    assert unpublished.version == listing.version + 1
