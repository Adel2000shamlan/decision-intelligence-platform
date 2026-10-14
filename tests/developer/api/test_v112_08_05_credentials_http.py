from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app
from app.modules.authentication.api import tokens


def issue_access_token(*, tenant_id=None):
    user_id = uuid4()
    access, _ = tokens.issue(user_id, tenant_id)
    return access


def create_application(client, tenant_id, token):
    response = client.post(
        "/api/v1/developer/applications",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "tenant_id": str(tenant_id),
            "name": "Credential Test Application",
        },
    )
    assert response.status_code == 201
    return response.json()


def test_create_credential_returns_secret_once_and_never_hash():
    tenant_id = uuid4()
    token = issue_access_token(tenant_id=tenant_id)

    with TestClient(app) as client:
        application = create_application(client, tenant_id, token)

        response = client.post(
            f"/api/v1/developer/applications/{application['id']}/credentials",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "client_id": "client-http-001",
                "scopes": ["projects:read"],
            },
        )

    assert response.status_code == 201
    data = response.json()

    assert data["tenant_id"] == str(tenant_id)
    assert data["application_id"] == application["id"]
    assert data["client_id"] == "client-http-001"
    assert data["scopes"] == ["projects:read"]
    assert data["status"] == "active"
    assert data["secret"]
    assert "secret_hash" not in data


def test_get_credential_never_returns_secret():
    tenant_id = uuid4()
    token = issue_access_token(tenant_id=tenant_id)

    with TestClient(app) as client:
        application = create_application(client, tenant_id, token)

        created = client.post(
            f"/api/v1/developer/applications/{application['id']}/credentials",
            headers={"Authorization": f"Bearer {token}"},
            json={"client_id": "client-http-002"},
        )
        assert created.status_code == 201

        credential_id = created.json()["id"]

        response = client.get(
            f"/api/v1/developer/credentials/{credential_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200
    data = response.json()

    assert data["id"] == credential_id
    assert data["client_id"] == "client-http-002"
    assert "secret" not in data
    assert "secret_hash" not in data


def test_list_application_credentials_is_tenant_scoped():
    tenant_a = uuid4()
    tenant_b = uuid4()
    token_a = issue_access_token(tenant_id=tenant_a)
    token_b = issue_access_token(tenant_id=tenant_b)

    with TestClient(app) as client:
        application_a = create_application(client, tenant_a, token_a)

        created = client.post(
            f"/api/v1/developer/applications/{application_a['id']}/credentials",
            headers={"Authorization": f"Bearer {token_a}"},
            json={"client_id": "client-http-003"},
        )
        assert created.status_code == 201
        credential_id = created.json()["id"]

        listed_a = client.get(
            f"/api/v1/developer/applications/{application_a['id']}/credentials",
            headers={"Authorization": f"Bearer {token_a}"},
        )
        assert listed_a.status_code == 200
        assert any(item["id"] == credential_id for item in listed_a.json())

        listed_b = client.get(
            f"/api/v1/developer/applications/{application_a['id']}/credentials",
            headers={"Authorization": f"Bearer {token_b}"},
        )

    assert listed_b.status_code == 404


def test_rotate_credential_replaces_secret_and_increments_version():
    tenant_id = uuid4()
    token = issue_access_token(tenant_id=tenant_id)

    with TestClient(app) as client:
        application = create_application(client, tenant_id, token)

        created = client.post(
            f"/api/v1/developer/applications/{application['id']}/credentials",
            headers={"Authorization": f"Bearer {token}"},
            json={"client_id": "client-http-004"},
        )
        assert created.status_code == 201

        original = created.json()

        rotated = client.post(
            f"/api/v1/developer/credentials/{original['id']}/rotate",
            headers={"Authorization": f"Bearer {token}"},
            json={"scopes": ["projects:read", "projects:write"]},
        )

    assert rotated.status_code == 200
    data = rotated.json()

    assert data["id"] == original["id"]
    assert data["client_id"] == original["client_id"]
    assert data["version"] == original["version"] + 1
    assert data["secret"]
    assert data["secret"] != original["secret"]
    assert data["scopes"] == ["projects:read", "projects:write"]
    assert "secret_hash" not in data


def test_revoke_credential_changes_status():
    tenant_id = uuid4()
    token = issue_access_token(tenant_id=tenant_id)

    with TestClient(app) as client:
        application = create_application(client, tenant_id, token)

        created = client.post(
            f"/api/v1/developer/applications/{application['id']}/credentials",
            headers={"Authorization": f"Bearer {token}"},
            json={"client_id": "client-http-005"},
        )
        assert created.status_code == 201
        credential_id = created.json()["id"]

        revoked = client.post(
            f"/api/v1/developer/credentials/{credential_id}/revoke",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert revoked.status_code == 200
    data = revoked.json()

    assert data["id"] == credential_id
    assert data["status"] == "revoked"
    assert data["revoked_at"] is not None
    assert "secret" not in data
    assert "secret_hash" not in data


def test_revoked_credential_cannot_be_rotated():
    tenant_id = uuid4()
    token = issue_access_token(tenant_id=tenant_id)

    with TestClient(app) as client:
        application = create_application(client, tenant_id, token)

        created = client.post(
            f"/api/v1/developer/applications/{application['id']}/credentials",
            headers={"Authorization": f"Bearer {token}"},
            json={"client_id": "client-http-006"},
        )
        assert created.status_code == 201
        credential_id = created.json()["id"]

        revoked = client.post(
            f"/api/v1/developer/credentials/{credential_id}/revoke",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert revoked.status_code == 200

        response = client.post(
            f"/api/v1/developer/credentials/{credential_id}/rotate",
            headers={"Authorization": f"Bearer {token}"},
            json={},
        )

    assert response.status_code == 409


def test_cross_tenant_credential_is_not_found():
    tenant_a = uuid4()
    tenant_b = uuid4()
    token_a = issue_access_token(tenant_id=tenant_a)
    token_b = issue_access_token(tenant_id=tenant_b)

    with TestClient(app) as client:
        application_a = create_application(client, tenant_a, token_a)

        created = client.post(
            f"/api/v1/developer/applications/{application_a['id']}/credentials",
            headers={"Authorization": f"Bearer {token_a}"},
            json={"client_id": "client-http-007"},
        )
        assert created.status_code == 201
        credential_id = created.json()["id"]

        response = client.get(
            f"/api/v1/developer/credentials/{credential_id}",
            headers={"Authorization": f"Bearer {token_b}"},
        )

    assert response.status_code == 404
