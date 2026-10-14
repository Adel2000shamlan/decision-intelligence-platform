from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app
from app.modules.authentication.api import tokens


def issue_access_token(tenant_id):
    user_id = uuid4()
    access_token, _ = tokens.issue(user_id, tenant_id)
    return access_token


def auth_headers(tenant_id):
    return {
        "Authorization": f"Bearer {issue_access_token(tenant_id)}",
    }


def payload(**overrides):
    value = {
        "organization_id": None,
        "display_name": "Acme Decision Intelligence",
        "short_name": "ACME",
        "description": "Tenant white-label configuration",
        "logo_url": "https://example.com/logo.png",
        "favicon_url": "https://example.com/favicon.ico",
        "primary_color": "#112233",
        "secondary_color": "#445566",
        "background_color": "#FFFFFF",
        "theme_color": "#112233",
        "locale": "en",
        "direction": "ltr",
    }
    value.update(overrides)
    return value


def test_white_label_routes_are_exposed_in_openapi():
    with TestClient(app) as client:
        response = client.get("/openapi.json")

    assert response.status_code == 200

    operations = response.json()["paths"]["/api/v1/white-label"]
    assert set(operations) == {"get", "post", "put", "delete"}


def test_white_label_requires_authentication():
    with TestClient(app) as client:
        response = client.get("/api/v1/white-label")

    assert response.status_code == 401
    assert response.json()["detail"] == "authentication required"
    assert response.headers["www-authenticate"] == "Bearer"


def test_white_label_create_get_and_update():
    tenant_id = uuid4()

    with TestClient(app) as client:
        headers = auth_headers(tenant_id)

        create_response = client.post(
            "/api/v1/white-label",
            headers=headers,
            json=payload(),
        )

        assert create_response.status_code == 201

        created = create_response.json()
        assert created["tenant_id"] == str(tenant_id)
        assert created["display_name"] == "Acme Decision Intelligence"
        assert created["short_name"] == "ACME"
        assert created["primary_color"] == "#112233"
        assert created["locale"] == "en"
        assert created["direction"] == "ltr"
        assert created["version"] == 1

        get_response = client.get(
            "/api/v1/white-label",
            headers=headers,
        )

        assert get_response.status_code == 200
        assert get_response.json()["id"] == created["id"]

        update_response = client.put(
            "/api/v1/white-label",
            headers=headers,
            json=payload(
                display_name="Acme Intelligence",
                short_name="AID",
                primary_color="#AABBCC",
                locale="ar",
                direction="rtl",
            ),
        )

        assert update_response.status_code == 200

        updated = update_response.json()
        assert updated["id"] == created["id"]
        assert updated["display_name"] == "Acme Intelligence"
        assert updated["short_name"] == "AID"
        assert updated["primary_color"] == "#aabbcc"
        assert updated["locale"] == "ar"
        assert updated["direction"] == "rtl"
        assert updated["version"] == 2


def test_white_label_duplicate_create_is_conflict():
    tenant_id = uuid4()

    with TestClient(app) as client:
        headers = auth_headers(tenant_id)

        first = client.post(
            "/api/v1/white-label",
            headers=headers,
            json=payload(),
        )

        assert first.status_code == 201

        second = client.post(
            "/api/v1/white-label",
            headers=headers,
            json=payload(
                display_name="Second Configuration",
            ),
        )

        assert second.status_code == 409


def test_white_label_is_tenant_scoped():
    tenant_a = uuid4()
    tenant_b = uuid4()

    with TestClient(app) as client:
        response_a = client.post(
            "/api/v1/white-label",
            headers=auth_headers(tenant_a),
            json=payload(
                display_name="Tenant A",
                short_name="A",
            ),
        )

        response_b = client.post(
            "/api/v1/white-label",
            headers=auth_headers(tenant_b),
            json=payload(
                display_name="Tenant B",
                short_name="B",
            ),
        )

        assert response_a.status_code == 201
        assert response_b.status_code == 201

        get_a = client.get(
            "/api/v1/white-label",
            headers=auth_headers(tenant_a),
        )
        get_b = client.get(
            "/api/v1/white-label",
            headers=auth_headers(tenant_b),
        )

        assert get_a.status_code == 200
        assert get_b.status_code == 200
        assert get_a.json()["tenant_id"] == str(tenant_a)
        assert get_b.json()["tenant_id"] == str(tenant_b)
        assert get_a.json()["display_name"] == "Tenant A"
        assert get_b.json()["display_name"] == "Tenant B"


def test_white_label_delete_requires_strong_authorization():
    tenant_id = uuid4()

    with TestClient(app) as client:
        headers = auth_headers(tenant_id)

        create_response = client.post(
            "/api/v1/white-label",
            headers=headers,
            json=payload(),
        )

        assert create_response.status_code == 201

        delete_response = client.delete(
            "/api/v1/white-label",
            headers=headers,
        )

        assert delete_response.status_code == 403

        get_response = client.get(
            "/api/v1/white-label",
            headers=headers,
        )

        assert get_response.status_code == 200
        assert get_response.json()["version"] == 1
