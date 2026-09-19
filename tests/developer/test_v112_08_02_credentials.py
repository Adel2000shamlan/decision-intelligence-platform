from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from app.modules.developer.domain.models import (
    APIScope,
    DeveloperCredentialStatus,
)
from app.modules.developer.security.credentials import (
    DeveloperCredentialSecurityService,
)


def test_issue_returns_raw_secret_but_credential_stores_only_hash():
    service = DeveloperCredentialSecurityService()

    issued = service.issue(
        tenant_id=uuid4(),
        application_id=uuid4(),
        client_id="client-001",
        scopes=(APIScope.PROJECTS_READ,),
    )

    assert issued.secret
    assert issued.secret not in issued.credential.secret_hash
    assert issued.credential.status is DeveloperCredentialStatus.ACTIVE


def test_issued_secret_verifies():
    service = DeveloperCredentialSecurityService()

    issued = service.issue(
        tenant_id=uuid4(),
        application_id=uuid4(),
        client_id="client-002",
    )

    assert service.verify(issued.credential, issued.secret) is True


def test_wrong_secret_is_rejected():
    service = DeveloperCredentialSecurityService()

    issued = service.issue(
        tenant_id=uuid4(),
        application_id=uuid4(),
        client_id="client-003",
    )

    assert service.verify(issued.credential, "wrong-secret") is False


def test_expired_credential_is_rejected():
    service = DeveloperCredentialSecurityService()
    created = datetime.now(timezone.utc)

    issued = service.issue(
        tenant_id=uuid4(),
        application_id=uuid4(),
        client_id="client-004",
        expires_at=created + timedelta(minutes=5),
    )

    assert service.verify(
        issued.credential,
        issued.secret,
        now=created + timedelta(minutes=6),
    ) is False


def test_revoked_credential_is_rejected():
    service = DeveloperCredentialSecurityService()

    issued = service.issue(
        tenant_id=uuid4(),
        application_id=uuid4(),
        client_id="client-005",
    )

    revoked = service.revoke(issued.credential)

    assert revoked.status is DeveloperCredentialStatus.REVOKED
    assert service.verify(revoked, issued.secret) is False


def test_rotation_creates_new_secret_and_invalidates_old_secret():
    service = DeveloperCredentialSecurityService()

    issued = service.issue(
        tenant_id=uuid4(),
        application_id=uuid4(),
        client_id="client-006",
    )

    rotated = service.rotate(issued.credential)

    assert rotated.secret != issued.secret
    assert rotated.credential.version == issued.credential.version + 1

    assert service.verify(issued.credential, issued.secret) is True
    assert service.verify(issued.credential, rotated.secret) is False
    assert service.verify(rotated.credential, rotated.secret) is True


def test_rotation_preserves_identity_and_application():
    service = DeveloperCredentialSecurityService()
    tenant_id = uuid4()
    application_id = uuid4()

    issued = service.issue(
        tenant_id=tenant_id,
        application_id=application_id,
        client_id="client-007",
    )

    rotated = service.rotate(issued.credential)

    assert rotated.credential.id == issued.credential.id
    assert rotated.credential.tenant_id == tenant_id
    assert rotated.credential.application_id == application_id
    assert rotated.credential.client_id == "client-007"


def test_non_active_credential_cannot_be_rotated():
    service = DeveloperCredentialSecurityService()

    issued = service.issue(
        tenant_id=uuid4(),
        application_id=uuid4(),
        client_id="client-008",
    )

    revoked = service.revoke(issued.credential)

    with pytest.raises(ValueError):
        service.rotate(revoked)


def test_naive_verification_time_is_rejected():
    service = DeveloperCredentialSecurityService()

    issued = service.issue(
        tenant_id=uuid4(),
        application_id=uuid4(),
        client_id="client-009",
    )

    with pytest.raises(ValueError):
        service.verify(
            issued.credential,
            issued.secret,
            now=datetime.now(),
        )
