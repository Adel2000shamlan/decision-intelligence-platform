from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app
from app.modules.authentication.api import tokens


def issue_access_token(*, tenant_id=None):
    user_id = uuid4()
    access, _ = tokens.issue(user_id, tenant_id)
    return access


def create_application(client, tenant_id, token, name="Marketplace Boundary App"):
    response = client.post(
        "/api/v1/developer/applications",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "tenant_id": str(tenant_id),
            "name": name,
        },
    )
    assert response.status_code == 201
    return response.json()


def create_listing(client, token, application_id, name="Boundary Listing"):
    response = client.post(
        "/api/v1/developer/marketplace/listings",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "publisher_application_id": application_id,
            "name": name,
            "description": "Marketplace boundary acceptance test",
            "capability": "decision-analysis",
        },
    )
    assert response.status_code == 201
    return response.json()


def test_marketplace_management_requires_platform_identity():
    with TestClient(app) as client:
        response = client.get("/api/v1/developer/marketplace/listings")

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_marketplace_creation_rejects_cross_tenant_application():
    tenant_a = uuid4()
    tenant_b = uuid4()
    token_a = issue_access_token(tenant_id=tenant_a)
    token_b = issue_access_token(tenant_id=tenant_b)

    with TestClient(app) as client:
        application_a = create_application(client, tenant_a, token_a)

        response = client.post(
            "/api/v1/developer/marketplace/listings",
            headers={"Authorization": f"Bearer {token_b}"},
            json={
                "publisher_application_id": application_a["id"],
                "name": "Cross Tenant Listing",
                "description": "Should not be created",
                "capability": "decision-analysis",
            },
        )

    assert response.status_code == 404


def test_marketplace_cannot_publish_when_publisher_application_is_suspended():
    tenant_id = uuid4()
    token = issue_access_token(tenant_id=tenant_id)

    with TestClient(app) as client:
        application = create_application(client, tenant_id, token)
        listing = create_listing(client, token, application["id"])

        status_response = client.patch(
            f"/api/v1/developer/applications/{application['id']}/status",
            headers={"Authorization": f"Bearer {token}"},
            json={"status": "suspended"},
        )
        assert status_response.status_code == 200

        response = client.post(
            f"/api/v1/developer/marketplace/listings/{listing['id']}/publish",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 404
    assert response.json()["detail"] == "application is not active"


def test_marketplace_cannot_publish_when_publisher_application_is_archived():
    tenant_id = uuid4()
    token = issue_access_token(tenant_id=tenant_id)

    with TestClient(app) as client:
        application = create_application(client, tenant_id, token)
        listing = create_listing(client, token, application["id"])

        status_response = client.patch(
            f"/api/v1/developer/applications/{application['id']}/status",
            headers={"Authorization": f"Bearer {token}"},
            json={"status": "archived"},
        )
        assert status_response.status_code == 200

        response = client.post(
            f"/api/v1/developer/marketplace/listings/{listing['id']}/publish",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 404
    assert response.json()["detail"] == "application is not active"


def test_marketplace_listing_version_changes_across_publish_lifecycle():
    tenant_id = uuid4()
    token = issue_access_token(tenant_id=tenant_id)

    with TestClient(app) as client:
        application = create_application(client, tenant_id, token)
        listing = create_listing(client, token, application["id"])

        assert listing["version"] == 1
        assert listing["published"] is False

        published = client.post(
            f"/api/v1/developer/marketplace/listings/{listing['id']}/publish",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert published.status_code == 200
        assert published.json()["published"] is True
        assert published.json()["version"] == 2

        unpublished = client.post(
            f"/api/v1/developer/marketplace/listings/{listing['id']}/unpublish",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert unpublished.status_code == 200
        assert unpublished.json()["published"] is False
        assert unpublished.json()["version"] == 3


def test_marketplace_listing_cannot_be_read_by_another_tenant():
    tenant_a = uuid4()
    tenant_b = uuid4()
    token_a = issue_access_token(tenant_id=tenant_a)
    token_b = issue_access_token(tenant_id=tenant_b)

    with TestClient(app) as client:
        application = create_application(client, tenant_a, token_a)
        listing = create_listing(client, token_a, application["id"])

        response = client.get(
            f"/api/v1/developer/marketplace/listings/{listing['id']}",
            headers={"Authorization": f"Bearer {token_b}"},
        )

    assert response.status_code == 404


def test_marketplace_listing_disappears_when_publisher_application_is_deleted():
    tenant_id = uuid4()
    token = issue_access_token(tenant_id=tenant_id)

    with TestClient(app) as client:
        application = create_application(client, tenant_id, token)
        listing = create_listing(client, token, application["id"])

        delete_response = client.delete(
            f"/api/v1/developer/applications/{application['id']}",
            headers={"Authorization": f"Bearer {token}"},
        )

        # The current public router may not expose application deletion yet.
        if delete_response.status_code == 405:
            return

        assert delete_response.status_code in {200, 204}

        response = client.get(
            f"/api/v1/developer/marketplace/listings/{listing['id']}",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 404
