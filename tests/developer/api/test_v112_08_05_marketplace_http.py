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
            "name": "Marketplace Test Application",
        },
    )
    assert response.status_code == 201
    return response.json()


def create_listing(client, tenant_id, token, application_id):
    response = client.post(
        "/api/v1/developer/marketplace/listings",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "publisher_application_id": application_id,
            "name": "Decision Analysis API",
            "description": "Decision intelligence capability",
            "capability": "decision-analysis",
        },
    )
    assert response.status_code == 201
    return response.json()


def test_create_listing_starts_unpublished():
    tenant_id = uuid4()
    token = issue_access_token(tenant_id=tenant_id)

    with TestClient(app) as client:
        application = create_application(client, tenant_id, token)
        response = client.post(
            "/api/v1/developer/marketplace/listings",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "publisher_application_id": application["id"],
                "name": "Decision Analysis API",
                "description": "Decision intelligence capability",
                "capability": "decision-analysis",
            },
        )

    assert response.status_code == 201
    data = response.json()
    assert data["tenant_id"] == str(tenant_id)
    assert data["publisher_application_id"] == application["id"]
    assert data["name"] == "Decision Analysis API"
    assert data["published"] is False
    assert "secret" not in data


def test_listings_are_tenant_scoped():
    tenant_a = uuid4()
    tenant_b = uuid4()
    token_a = issue_access_token(tenant_id=tenant_a)
    token_b = issue_access_token(tenant_id=tenant_b)

    with TestClient(app) as client:
        application_a = create_application(client, tenant_a, token_a)
        listing = create_listing(
            client,
            tenant_a,
            token_a,
            application_a["id"],
        )

        listed_a = client.get(
            "/api/v1/developer/marketplace/listings",
            headers={"Authorization": f"Bearer {token_a}"},
        )
        assert listed_a.status_code == 200
        assert any(
            item["id"] == listing["id"]
            for item in listed_a.json()
        )

        listed_b = client.get(
            "/api/v1/developer/marketplace/listings",
            headers={"Authorization": f"Bearer {token_b}"},
        )

    assert listed_b.status_code == 200
    assert all(
        item["id"] != listing["id"]
        for item in listed_b.json()
    )


def test_get_listing_is_tenant_scoped():
    tenant_a = uuid4()
    tenant_b = uuid4()
    token_a = issue_access_token(tenant_id=tenant_a)
    token_b = issue_access_token(tenant_id=tenant_b)

    with TestClient(app) as client:
        application_a = create_application(client, tenant_a, token_a)
        listing = create_listing(
            client,
            tenant_a,
            token_a,
            application_a["id"],
        )

        own = client.get(
            f"/api/v1/developer/marketplace/listings/{listing['id']}",
            headers={"Authorization": f"Bearer {token_a}"},
        )
        assert own.status_code == 200

        foreign = client.get(
            f"/api/v1/developer/marketplace/listings/{listing['id']}",
            headers={"Authorization": f"Bearer {token_b}"},
        )

    assert foreign.status_code == 404


def test_publish_and_unpublish_listing():
    tenant_id = uuid4()
    token = issue_access_token(tenant_id=tenant_id)

    with TestClient(app) as client:
        application = create_application(client, tenant_id, token)
        listing = create_listing(
            client,
            tenant_id,
            token,
            application["id"],
        )

        published = client.post(
            f"/api/v1/developer/marketplace/listings/{listing['id']}/publish",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert published.status_code == 200
        assert published.json()["published"] is True

        unpublished = client.post(
            f"/api/v1/developer/marketplace/listings/{listing['id']}/unpublish",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert unpublished.status_code == 200
    assert unpublished.json()["published"] is False


def test_cross_tenant_application_cannot_publish_listing():
    tenant_a = uuid4()
    tenant_b = uuid4()
    token_a = issue_access_token(tenant_id=tenant_a)
    token_b = issue_access_token(tenant_id=tenant_b)

    with TestClient(app) as client:
        application_a = create_application(client, tenant_a, token_a)
        listing = create_listing(
            client,
            tenant_a,
            token_a,
            application_a["id"],
        )

        response = client.post(
            f"/api/v1/developer/marketplace/listings/{listing['id']}/publish",
            headers={"Authorization": f"Bearer {token_b}"},
        )

    assert response.status_code == 404
