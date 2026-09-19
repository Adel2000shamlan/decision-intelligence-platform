from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app
from app.modules.authentication.api import tokens
from app.modules.developer.api.resources import configure_resource_rate_controller
from app.modules.developer.usage.rate_control import DeveloperRateController
from app.infrastructure.gateway import RateLimiter
from app.modules.organization.domain.models import Organization
import app.modules.organization.api.router as organization_router
from app.modules.project.domain.models import Project
import app.modules.project.api.router as project_router


def _platform_headers(tenant_id):
    user_id = uuid4()
    access_token, _ = tokens.issue(user_id, tenant_id)
    return {
        "Authorization": f"Bearer {access_token}",
    }


def _create_application(client, tenant_id, name):
    response = client.post(
        "/api/v1/developer/applications",
        headers=_platform_headers(tenant_id),
        json={
            "tenant_id": str(tenant_id),
            "name": name,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _create_credential(client, tenant_id, application_id, client_id, scopes):
    response = client.post(
        f"/api/v1/developer/applications/{application_id}/credentials",
        headers=_platform_headers(tenant_id),
        json={
            "client_id": client_id,
            "scopes": scopes,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _seed_project(tenant_id):
    organization = Organization.create(
        name=f"Developer Integration Org {uuid4()}",
        slug=f"developer-integration-{uuid4()}",
    )
    organization_router._service.repository.save(
        organization,
        tenant_id=tenant_id,
    )

    project = Project.create(
        organization.id,
        f"Developer Integration Project {uuid4()}",
    )
    project_router._repo.save(project)

    return project


def _developer_resource_headers(client_id, secret):
    return {
        "X-Developer-Client-ID": client_id,
        "X-Developer-Secret": secret,
    }


def test_http_rate_limit_returns_429_after_application_bucket_is_exhausted():
    tenant_id = uuid4()

    with TestClient(app) as client:
        application = _create_application(
            client,
            tenant_id,
            f"Rate Limited App {uuid4()}",
        )
        credential = _create_credential(
            client,
            tenant_id,
            application["id"],
            f"rate-client-{uuid4()}",
            ["projects:read"],
        )

        project = _seed_project(tenant_id)

        configure_resource_rate_controller(
            DeveloperRateController(
                limiter=RateLimiter(limit=1, window=60),
            )
        )

        headers = {
            **_platform_headers(tenant_id),
            **_developer_resource_headers(
                credential["client_id"],
                credential["secret"],
            ),
        }

        first = client.get(
            f"/api/v1/developer/resources/projects/{project.id}",
            headers=headers,
        )
        second = client.get(
            f"/api/v1/developer/resources/projects/{project.id}",
            headers=headers,
        )

        assert first.status_code == 200, first.text
        assert first.json()["id"] == str(project.id)
        assert "secret" not in first.json()
        assert "secret_hash" not in first.json()

        assert second.status_code == 429
        assert second.json()["detail"] == "developer rate limit exceeded"


def test_invalid_developer_secret_does_not_consume_rate_limit_capacity():
    tenant_id = uuid4()

    with TestClient(app) as client:
        application = _create_application(
            client,
            tenant_id,
            f"Credential Isolation App {uuid4()}",
        )
        credential = _create_credential(
            client,
            tenant_id,
            application["id"],
            f"isolation-client-{uuid4()}",
            ["projects:read"],
        )

        project = _seed_project(tenant_id)

        configure_resource_rate_controller(
            DeveloperRateController(
                limiter=RateLimiter(limit=1, window=60),
            )
        )

        invalid_headers = {
            **_platform_headers(tenant_id),
            **_developer_resource_headers(
                credential["client_id"],
                "definitely-invalid-secret",
            ),
        }

        invalid = client.get(
            f"/api/v1/developer/resources/projects/{project.id}",
            headers=invalid_headers,
        )

        assert invalid.status_code == 401

        valid_headers = {
            **_platform_headers(tenant_id),
            **_developer_resource_headers(
                credential["client_id"],
                credential["secret"],
            ),
        }

        valid = client.get(
            f"/api/v1/developer/resources/projects/{project.id}",
            headers=valid_headers,
        )
        limited = client.get(
            f"/api/v1/developer/resources/projects/{project.id}",
            headers=valid_headers,
        )

        assert valid.status_code == 200, valid.text
        assert limited.status_code == 429


def test_http_rate_limit_isolated_between_applications():
    tenant_id = uuid4()

    with TestClient(app) as client:
        application_a = _create_application(
            client,
            tenant_id,
            f"Application A {uuid4()}",
        )
        application_b = _create_application(
            client,
            tenant_id,
            f"Application B {uuid4()}",
        )

        credential_a = _create_credential(
            client,
            tenant_id,
            application_a["id"],
            f"client-a-{uuid4()}",
            ["projects:read"],
        )
        credential_b = _create_credential(
            client,
            tenant_id,
            application_b["id"],
            f"client-b-{uuid4()}",
            ["projects:read"],
        )

        project = _seed_project(tenant_id)

        configure_resource_rate_controller(
            DeveloperRateController(
                limiter=RateLimiter(limit=1, window=60),
            )
        )

        headers_a = {
            **_platform_headers(tenant_id),
            **_developer_resource_headers(
                credential_a["client_id"],
                credential_a["secret"],
            ),
        }
        headers_b = {
            **_platform_headers(tenant_id),
            **_developer_resource_headers(
                credential_b["client_id"],
                credential_b["secret"],
            ),
        }

        first_a = client.get(
            f"/api/v1/developer/resources/projects/{project.id}",
            headers=headers_a,
        )
        second_a = client.get(
            f"/api/v1/developer/resources/projects/{project.id}",
            headers=headers_a,
        )
        first_b = client.get(
            f"/api/v1/developer/resources/projects/{project.id}",
            headers=headers_b,
        )

        assert first_a.status_code == 200, first_a.text
        assert second_a.status_code == 429
        assert first_b.status_code == 200, first_b.text


def test_http_rate_limit_isolated_between_tenants():
    tenant_a = uuid4()
    tenant_b = uuid4()

    with TestClient(app) as client:
        application_a = _create_application(
            client,
            tenant_a,
            f"Tenant A App {uuid4()}",
        )
        application_b = _create_application(
            client,
            tenant_b,
            f"Tenant B App {uuid4()}",
        )

        credential_a = _create_credential(
            client,
            tenant_a,
            application_a["id"],
            f"tenant-a-client-{uuid4()}",
            ["projects:read"],
        )
        credential_b = _create_credential(
            client,
            tenant_b,
            application_b["id"],
            f"tenant-b-client-{uuid4()}",
            ["projects:read"],
        )

        project_a = _seed_project(tenant_a)
        project_b = _seed_project(tenant_b)

        configure_resource_rate_controller(
            DeveloperRateController(
                limiter=RateLimiter(limit=1, window=60),
            )
        )

        headers_a = {
            **_platform_headers(tenant_a),
            **_developer_resource_headers(
                credential_a["client_id"],
                credential_a["secret"],
            ),
        }
        headers_b = {
            **_platform_headers(tenant_b),
            **_developer_resource_headers(
                credential_b["client_id"],
                credential_b["secret"],
            ),
        }

        first_a = client.get(
            f"/api/v1/developer/resources/projects/{project_a.id}",
            headers=headers_a,
        )
        second_a = client.get(
            f"/api/v1/developer/resources/projects/{project_a.id}",
            headers=headers_a,
        )
        first_b = client.get(
            f"/api/v1/developer/resources/projects/{project_b.id}",
            headers=headers_b,
        )

        assert first_a.status_code == 200, first_a.text
        assert second_a.status_code == 429
        assert first_b.status_code == 200, first_b.text
