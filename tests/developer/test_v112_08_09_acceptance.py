from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app
from app.modules.authentication.api import tokens
from app.modules.developer.api.resources import configure_resource_rate_controller
from app.modules.developer.usage.rate_control import DeveloperRateController
from app.infrastructure.gateway import RateLimiter


def issue_platform_token(*, tenant_id):
    user_id = uuid4()
    access, _ = tokens.issue(user_id, tenant_id)
    return access


def test_developer_platform_end_to_end_application_credential_marketplace():
    tenant_id = uuid4()
    token = issue_platform_token(tenant_id=tenant_id)

    with TestClient(app) as client:
        application_response = client.post(
            "/api/v1/developer/applications",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "tenant_id": str(tenant_id),
                "name": "Acceptance Application",
            },
        )

        assert application_response.status_code == 201
        application = application_response.json()
        assert application["tenant_id"] == str(tenant_id)
        assert application["status"] == "active"
        assert "secret_hash" not in application

        credential_response = client.post(
            f"/api/v1/developer/applications/{application['id']}/credentials",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "client_id": "acceptance-client",
                "scopes": ["projects:read"],
            },
        )

        assert credential_response.status_code == 201
        credential = credential_response.json()
        assert credential["client_id"] == "acceptance-client"
        assert credential["status"] == "active"
        assert credential["scopes"] == ["projects:read"]
        assert credential.get("secret")

        secret = credential["secret"]

        credential_read = client.get(
            f"/api/v1/developer/credentials/{credential['id']}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert credential_read.status_code == 200
        assert "secret" not in credential_read.json()
        assert "secret_hash" not in credential_read.json()

        listing_response = client.post(
            "/api/v1/developer/marketplace/listings",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "publisher_application_id": application["id"],
                "name": "Acceptance Listing",
                "description": "Developer acceptance listing",
                "capability": "decision-analysis",
            },
        )

        assert listing_response.status_code == 201
        listing = listing_response.json()
        assert listing["published"] is False

        publish_response = client.post(
            f"/api/v1/developer/marketplace/listings/{listing['id']}/publish",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert publish_response.status_code == 200
        assert publish_response.json()["published"] is True

        assert secret


def test_developer_platform_cross_tenant_isolation():
    tenant_a = uuid4()
    tenant_b = uuid4()

    token_a = issue_platform_token(tenant_id=tenant_a)
    token_b = issue_platform_token(tenant_id=tenant_b)

    with TestClient(app) as client:
        application_response = client.post(
            "/api/v1/developer/applications",
            headers={"Authorization": f"Bearer {token_a}"},
            json={
                "tenant_id": str(tenant_a),
                "name": "Tenant A Application",
            },
        )
        assert application_response.status_code == 201
        application = application_response.json()

        cross_tenant_listing = client.post(
            "/api/v1/developer/marketplace/listings",
            headers={"Authorization": f"Bearer {token_b}"},
            json={
                "publisher_application_id": application["id"],
                "name": "Cross Tenant",
                "description": "Must be rejected",
                "capability": "decision-analysis",
            },
        )

        assert cross_tenant_listing.status_code == 404

        cross_tenant_application = client.get(
            f"/api/v1/developer/applications/{application['id']}",
            headers={"Authorization": f"Bearer {token_b}"},
        )

        assert cross_tenant_application.status_code == 404


def test_developer_resource_requires_platform_and_developer_credentials():
    tenant_id = uuid4()
    token = issue_platform_token(tenant_id=tenant_id)

    with TestClient(app) as client:
        application_response = client.post(
            "/api/v1/developer/applications",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "tenant_id": str(tenant_id),
                "name": "Resource Acceptance Application",
            },
        )
        assert application_response.status_code == 201
        application = application_response.json()

        credential_response = client.post(
            f"/api/v1/developer/applications/{application['id']}/credentials",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "client_id": "resource-acceptance-client",
                "scopes": ["projects:read"],
            },
        )
        assert credential_response.status_code == 201
        credential = credential_response.json()

        response_without_developer_credential = client.get(
            "/api/v1/developer/resources/projects/00000000-0000-0000-0000-000000000000",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response_without_developer_credential.status_code == 401

        response_with_invalid_developer_secret = client.get(
            "/api/v1/developer/resources/projects/00000000-0000-0000-0000-000000000000",
            headers={
                "Authorization": f"Bearer {token}",
                "X-Developer-Client-ID": credential["client_id"],
                "X-Developer-Secret": "invalid-secret",
            },
        )

        assert response_with_invalid_developer_secret.status_code == 401


def test_developer_rate_limit_is_enforced_after_credential_authentication():
    tenant_id = uuid4()
    token = issue_platform_token(tenant_id=tenant_id)

    try:
        with TestClient(app) as client:
            configure_resource_rate_controller(
                DeveloperRateController(
                    limiter=RateLimiter(limit=1, window=60),
                )
            )
            application_response = client.post(
                "/api/v1/developer/applications",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "tenant_id": str(tenant_id),
                    "name": "Rate Acceptance Application",
                },
            )
            assert application_response.status_code == 201
            application = application_response.json()

            credential_response = client.post(
                f"/api/v1/developer/applications/{application['id']}/credentials",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "client_id": "rate-acceptance-client",
                    "scopes": ["projects:read"],
                },
            )
            assert credential_response.status_code == 201
            credential = credential_response.json()

            headers = {
                "Authorization": f"Bearer {token}",
                "X-Developer-Client-ID": credential["client_id"],
                "X-Developer-Secret": credential["secret"],
            }

            first = client.get(
                "/api/v1/developer/resources/projects/00000000-0000-0000-0000-000000000000",
                headers=headers,
            )
            second = client.get(
                "/api/v1/developer/resources/projects/00000000-0000-0000-0000-000000000000",
                headers=headers,
            )

            assert first.status_code in {403, 404}
            assert second.status_code == 429
    finally:
        configure_resource_rate_controller(DeveloperRateController())
