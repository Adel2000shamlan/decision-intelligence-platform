from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app
from app.modules.authentication.api import tokens


def issue_access_token(*, tenant_id=None):
    user_id = uuid4()
    access, _ = tokens.issue(user_id, tenant_id)
    return access


def test_create_application_requires_bearer_authentication():
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/developer/applications",
            json={
                "tenant_id": str(uuid4()),
                "name": "Test Developer App",
            },
        )

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_invalid_bearer_token_is_rejected():
    tenant_id = uuid4()

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/developer/applications",
            headers={"Authorization": "Bearer invalid-token"},
            json={
                "tenant_id": str(tenant_id),
                "name": "Test Developer App",
            },
        )

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_non_tenant_scoped_platform_token_is_rejected():
    token = issue_access_token()

    with TestClient(app) as client:
        response = client.get(
            "/api/v1/developer/applications",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 403


def test_tenant_scoped_identity_can_create_application():
    tenant_id = uuid4()
    token = issue_access_token(tenant_id=tenant_id)

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/developer/applications",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "tenant_id": str(tenant_id),
                "name": "Test Developer App",
            },
        )

    assert response.status_code == 201
    data = response.json()
    assert data["tenant_id"] == str(tenant_id)
    assert data["name"] == "Test Developer App"
    assert data["status"] == "active"
    assert "secret_hash" not in data


def test_tenant_mismatch_is_rejected():
    identity_tenant = uuid4()
    requested_tenant = uuid4()
    token = issue_access_token(tenant_id=identity_tenant)

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/developer/applications",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "tenant_id": str(requested_tenant),
                "name": "Cross Tenant App",
            },
        )

    assert response.status_code == 403


def test_application_listing_is_tenant_scoped():
    tenant_a = uuid4()
    tenant_b = uuid4()
    token_a = issue_access_token(tenant_id=tenant_a)
    token_b = issue_access_token(tenant_id=tenant_b)

    with TestClient(app) as client:
        created = client.post(
            "/api/v1/developer/applications",
            headers={"Authorization": f"Bearer {token_a}"},
            json={
                "tenant_id": str(tenant_a),
                "name": "Tenant A App",
            },
        )
        assert created.status_code == 201
        application_id = created.json()["id"]

        listed_a = client.get(
            "/api/v1/developer/applications",
            headers={"Authorization": f"Bearer {token_a}"},
        )
        assert listed_a.status_code == 200
        assert any(item["id"] == application_id for item in listed_a.json())

        listed_b = client.get(
            "/api/v1/developer/applications",
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert listed_b.status_code == 200
        assert all(item["id"] != application_id for item in listed_b.json())


def test_application_from_another_tenant_is_not_found():
    tenant_a = uuid4()
    tenant_b = uuid4()
    token_a = issue_access_token(tenant_id=tenant_a)
    token_b = issue_access_token(tenant_id=tenant_b)

    with TestClient(app) as client:
        created = client.post(
            "/api/v1/developer/applications",
            headers={"Authorization": f"Bearer {token_a}"},
            json={
                "tenant_id": str(tenant_a),
                "name": "Tenant A Private App",
            },
        )
        assert created.status_code == 201
        application_id = created.json()["id"]

        response = client.get(
            f"/api/v1/developer/applications/{application_id}",
            headers={"Authorization": f"Bearer {token_b}"},
        )

    assert response.status_code == 404
