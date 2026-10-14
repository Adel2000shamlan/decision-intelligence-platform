from datetime import datetime, timedelta, timezone
from uuid import uuid4
import sqlite3

import pytest
from fastapi import HTTPException

from app.modules.developer.api.router import DeveloperPrincipal
from app.modules.developer.application.service import DeveloperService
from app.modules.developer.authorization.http import (
    DeveloperCredentialPrincipal,
    authenticate_developer_credential,
)
from app.modules.developer.domain.models import APIScope
from app.modules.developer.persistence.sqlite import SQLiteDeveloperRepository


def _platform(tenant_id):
    class Platform:
        pass

    platform = Platform()
    platform.tenant_id = tenant_id
    return platform


@pytest.fixture
def service():
    connection = sqlite3.connect(":memory:")
    try:
        yield DeveloperService(SQLiteDeveloperRepository(connection))
    finally:
        connection.close()


def _credential(service, tenant_id, client_id="http-client"):
    application = service.create_application(
        tenant_id=tenant_id,
        name="HTTP Test Application",
    )
    issued = service.issue_credential(
        tenant_id=tenant_id,
        application_id=application.id,
        client_id=client_id,
        scopes=(APIScope.PROJECTS_READ,),
    )
    return issued


def test_valid_credential_returns_principal(service):
    tenant_id = uuid4()
    issued = _credential(service, tenant_id)

    result = authenticate_developer_credential(
        platform=_platform(tenant_id),
        service=service,
        client_id="http-client",
        secret=issued.secret,
    )

    assert isinstance(result, DeveloperCredentialPrincipal)
    assert result.credential.id == issued.credential.id
    assert result.secret == issued.secret


@pytest.mark.parametrize(
    ("client_id", "secret"),
    [
        (None, "secret"),
        ("", "secret"),
        ("   ", "secret"),
        ("http-client", None),
        ("http-client", ""),
    ],
)
def test_missing_credential_material_returns_401(
    service,
    client_id,
    secret,
):
    tenant_id = uuid4()

    with pytest.raises(HTTPException) as exc:
        authenticate_developer_credential(
            platform=_platform(tenant_id),
            service=service,
            client_id=client_id,
            secret=secret,
        )

    assert exc.value.status_code == 401


def test_unknown_client_returns_401(service):
    tenant_id = uuid4()

    with pytest.raises(HTTPException) as exc:
        authenticate_developer_credential(
            platform=_platform(tenant_id),
            service=service,
            client_id="unknown-client",
            secret="not-a-real-secret",
        )

    assert exc.value.status_code == 401


def test_wrong_secret_returns_401(service):
    tenant_id = uuid4()
    _credential(service, tenant_id)

    with pytest.raises(HTTPException) as exc:
        authenticate_developer_credential(
            platform=_platform(tenant_id),
            service=service,
            client_id="http-client",
            secret="wrong-secret",
        )

    assert exc.value.status_code == 401


def test_revoked_credential_returns_401(service):
    tenant_id = uuid4()
    issued = _credential(service, tenant_id)

    service.revoke_credential(
        tenant_id=tenant_id,
        credential_id=issued.credential.id,
    )

    with pytest.raises(HTTPException) as exc:
        authenticate_developer_credential(
            platform=_platform(tenant_id),
            service=service,
            client_id="http-client",
            secret=issued.secret,
        )

    assert exc.value.status_code == 401


def test_expired_credential_returns_401(service):
    tenant_id = uuid4()
    application = service.create_application(
        tenant_id=tenant_id,
        name="Expired HTTP Application",
    )
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=1)

    issued = service.issue_credential(
        tenant_id=tenant_id,
        application_id=application.id,
        client_id="expired-http-client",
        scopes=(APIScope.PROJECTS_READ,),
        expires_at=expires_at,
    )

    with pytest.raises(HTTPException) as exc:
        authenticate_developer_credential(
            platform=_platform(tenant_id),
            service=service,
            client_id="expired-http-client",
            secret=issued.secret,
            now=expires_at + timedelta(seconds=1),
        )

    assert exc.value.status_code == 401


def test_other_tenant_credential_is_not_disclosed(service):
    tenant_a = uuid4()
    tenant_b = uuid4()

    _credential(service, tenant_a, client_id="tenant-a-client")

    with pytest.raises(HTTPException) as exc:
        authenticate_developer_credential(
            platform=_platform(tenant_b),
            service=service,
            client_id="tenant-a-client",
            secret="anything",
        )

    assert exc.value.status_code == 401


def test_header_contract_is_not_embedded_in_authentication_function():
    """
    The authentication core deliberately accepts plain values.
    FastAPI Header extraction belongs at the HTTP router boundary.
    """
    assert "Header" not in authenticate_developer_credential.__annotations__
