from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_remains_public():
    response = client.get("/api/v1/health")
    assert response.status_code == 200


def test_project_list_requires_authentication():
    response = client.get(
        f"/api/v1/projects/organization/{uuid4()}"
    )
    assert response.status_code in (401, 403)


def test_project_detail_requires_authentication_even_if_missing():
    response = client.get(f"/api/v1/projects/{uuid4()}")
    assert response.status_code in (401, 403)


def test_organization_list_requires_authentication():
    response = client.get("/api/v1/organizations")
    assert response.status_code in (401, 403)


def test_risk_list_requires_authentication():
    response = client.get("/api/v1/risks")
    assert response.status_code in (401, 403)

from app.modules.authentication.api import users, credentials, rbac
from app.modules.identity.domain.models import User


def _security_test_headers(role, tenant_id):
    email = f"v114-{uuid4().hex}@example.com"
    user = User.create(email, "V114 Security Test User")
    users.save(user)
    credentials.register(user.id, "StrongPass123!")

    if role is not None:
        rbac.assign(user.id, role, tenant_id)

    response = client.post(
        "/auth/login",
        json={
            "email": email,
            "password": "StrongPass123!",
            "tenant_id": str(tenant_id),
        },
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_owner_can_create_project_in_own_tenant():
    tenant_id = uuid4()
    headers = _security_test_headers("owner", tenant_id)

    response = client.post(
        "/api/v1/projects",
        json={"organization_id": str(tenant_id), "name": "Owner Project"},
        headers=headers,
    )
    assert response.status_code == 200, response.text


def test_viewer_cannot_create_project():
    tenant_id = uuid4()
    headers = _security_test_headers("viewer", tenant_id)

    response = client.post(
        "/api/v1/projects",
        json={"organization_id": str(tenant_id), "name": "Forbidden Project"},
        headers=headers,
    )
    assert response.status_code == 403, response.text


def test_user_without_role_cannot_create_project():
    tenant_id = uuid4()
    headers = _security_test_headers(None, tenant_id)

    response = client.post(
        "/api/v1/projects",
        json={"organization_id": str(tenant_id), "name": "No Role Project"},
        headers=headers,
    )
    assert response.status_code == 403, response.text


def test_owner_cannot_create_project_in_another_tenant():
    tenant_id = uuid4()
    other_tenant_id = uuid4()
    headers = _security_test_headers("owner", tenant_id)

    response = client.post(
        "/api/v1/projects",
        json={
            "organization_id": str(other_tenant_id),
            "name": "Cross Tenant Project",
        },
        headers=headers,
    )
    assert response.status_code == 403, response.text


def test_other_tenant_cannot_read_project():
    owner_tenant = uuid4()
    other_tenant = uuid4()
    owner_headers = _security_test_headers("owner", owner_tenant)

    created = client.post(
        "/api/v1/projects",
        json={"organization_id": str(owner_tenant), "name": "Private Project"},
        headers=owner_headers,
    )
    assert created.status_code == 200, created.text

    other_headers = _security_test_headers("owner", other_tenant)
    project_id = created.json()["id"]

    response = client.get(
        f"/api/v1/projects/{project_id}",
        headers=other_headers,
    )
    assert response.status_code == 404, response.text


def test_other_tenant_cannot_create_decision_for_foreign_project():
    tenant_a = uuid4()
    tenant_b = uuid4()
    headers_a = _security_test_headers("owner", tenant_a)
    headers_b = _security_test_headers("owner", tenant_b)

    project = client.post(
        "/api/v1/projects",
        json={"organization_id": str(tenant_a), "name": f"Private-{uuid4().hex}"},
        headers=headers_a,
    )
    assert project.status_code == 200, project.text

    response = client.post(
        "/api/v1/decisions",
        json={
            "project_id": project.json()["id"],
            "title": "Foreign decision",
            "objective": "Must be denied",
        },
        headers=headers_b,
    )
    assert response.status_code in (403, 404), response.text


def test_other_tenant_cannot_create_risk_for_foreign_project():
    tenant_a = uuid4()
    tenant_b = uuid4()
    headers_a = _security_test_headers("owner", tenant_a)
    headers_b = _security_test_headers("owner", tenant_b)

    project = client.post(
        "/api/v1/projects",
        json={"organization_id": str(tenant_a), "name": f"Private-{uuid4().hex}"},
        headers=headers_a,
    )
    assert project.status_code == 200, project.text

    response = client.post(
        "/api/v1/risks",
        json={
            "project_id": project.json()["id"],
            "title": "Foreign risk",
            "probability": 0.5,
            "impact": 10,
        },
        headers=headers_b,
    )
    assert response.status_code in (403, 404), response.text


def test_risk_list_does_not_expose_another_tenants_records():
    tenant_a = uuid4()
    tenant_b = uuid4()
    headers_a = _security_test_headers("owner", tenant_a)
    headers_b = _security_test_headers("owner", tenant_b)

    project = client.post(
        "/api/v1/projects",
        json={"organization_id": str(tenant_a), "name": f"Private-{uuid4().hex}"},
        headers=headers_a,
    )
    assert project.status_code == 200, project.text

    created = client.post(
        "/api/v1/risks",
        json={
            "project_id": project.json()["id"],
            "title": f"Secret-risk-{uuid4().hex}",
            "probability": 0.5,
            "impact": 10,
        },
        headers=headers_a,
    )
    assert created.status_code == 200, created.text

    response = client.get("/api/v1/risks", headers=headers_b)
    assert response.status_code == 200, response.text
    assert all(
        item.get("id") != created.json()["id"]
        for item in response.json()
    )


def test_organization_creation_requires_authentication():
    response = client.post(
        "/api/v1/organizations",
        json={"name": "Unauthenticated Organization"},
    )
    assert response.status_code == 401, response.text


def test_viewer_cannot_create_organization():
    tenant_id = uuid4()
    headers = _security_test_headers("viewer", tenant_id)
    response = client.post(
        "/api/v1/organizations",
        json={"name": "Forbidden Organization"},
        headers=headers,
    )
    assert response.status_code == 403, response.text


def test_owner_can_create_organization_in_own_tenant():
    tenant_id = uuid4()
    headers = _security_test_headers("owner", tenant_id)
    response = client.post(
        "/api/v1/organizations",
        json={"name": "Private Organization"},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    assert response.json()["tenant_id"] == str(tenant_id)


def test_organization_list_is_scoped_to_current_tenant():
    tenant_a = uuid4()
    tenant_b = uuid4()
    headers_a = _security_test_headers("owner", tenant_a)
    headers_b = _security_test_headers("owner", tenant_b)

    created = client.post(
        "/api/v1/organizations",
        json={"name": f"Secret Org {uuid4().hex}"},
        headers=headers_a,
    )
    assert created.status_code == 200, created.text

    response = client.get("/api/v1/organizations", headers=headers_b)
    assert response.status_code == 200, response.text
    assert all(
        item["id"] != created.json()["id"]
        for item in response.json()
    )


def test_command_rejects_create_for_different_tenant():
    import pytest
    from app.modules.project.application.commands import (
        CreateProject,
        ProjectCommandHandler,
    )
    from app.modules.project.application.repository import ProjectRepositoryAdapter
    from app.modules.project.persistence.sqlite import SQLiteProjectRepository

    repository = ProjectRepositoryAdapter(SQLiteProjectRepository())
    handler = ProjectCommandHandler(repository)
    organization_id = uuid4()
    other_tenant_id = uuid4()

    with pytest.raises(PermissionError):
        handler.create(
            CreateProject(
                organization_id,
                "Cross Tenant Command",
                tenant_id=other_tenant_id,
            )
        )


def test_command_rejects_cross_tenant_mutation_without_repository_filter():
    import pytest
    from app.modules.project.application.commands import (
        CreateProject,
        ProjectCommandHandler,
        RenameProject,
    )
    from app.modules.project.application.repository import ProjectRepositoryAdapter
    from app.modules.project.persistence.sqlite import SQLiteProjectRepository

    backend = SQLiteProjectRepository()
    scoped_repository = ProjectRepositoryAdapter(backend)
    organization_id = uuid4()
    project = ProjectCommandHandler(scoped_repository).create(
        CreateProject(organization_id, "Protected Project")
    )

    class UnscopedRepository:
        def get_by_id(self, project_id, organization_id=None):
            return scoped_repository.get_by_id(project_id)

        def save(self, project, expected_version=None):
            return scoped_repository.save(project, expected_version)

        def exists_by_name(self, organization_id, name, exclude_id=None):
            return scoped_repository.exists_by_name(
                organization_id, name, exclude_id
            )

    handler = ProjectCommandHandler(UnscopedRepository())

    with pytest.raises(PermissionError):
        handler.rename(
            RenameProject(
                project.id,
                "Unauthorized Rename",
                tenant_id=uuid4(),
            )
        )

    assert scoped_repository.get_by_id(project.id).name == "Protected Project"
    backend.close()


def test_other_tenant_cannot_rename_project():
    owner_tenant = uuid4()
    other_tenant = uuid4()
    owner_headers = _security_test_headers("owner", owner_tenant)
    other_headers = _security_test_headers("owner", other_tenant)

    created = client.post(
        "/api/v1/projects",
        json={
            "organization_id": str(owner_tenant),
            "name": f"Protected Rename {uuid4().hex}",
        },
        headers=owner_headers,
    )
    assert created.status_code == 200, created.text
    project_id = created.json()["id"]
    original_name = created.json()["name"]

    response = client.patch(
        f"/api/v1/projects/{project_id}",
        json={"name": "Unauthorized Rename"},
        headers=other_headers,
    )
    assert response.status_code in (403, 404), response.text

    owner_read = client.get(
        f"/api/v1/projects/{project_id}",
        headers=owner_headers,
    )
    assert owner_read.status_code == 200, owner_read.text
    assert owner_read.json()["name"] == original_name


def test_other_tenant_cannot_transition_project():
    owner_tenant = uuid4()
    other_tenant = uuid4()
    owner_headers = _security_test_headers("owner", owner_tenant)
    other_headers = _security_test_headers("owner", other_tenant)

    created = client.post(
        "/api/v1/projects",
        json={
            "organization_id": str(owner_tenant),
            "name": f"Protected Transition {uuid4().hex}",
        },
        headers=owner_headers,
    )
    assert created.status_code == 200, created.text
    project_id = created.json()["id"]
    original_status = created.json()["status"]

    response = client.post(
        f"/api/v1/projects/{project_id}/transition",
        json={"status": "active"},
        headers=other_headers,
    )
    assert response.status_code in (403, 404), response.text

    owner_read = client.get(
        f"/api/v1/projects/{project_id}",
        headers=owner_headers,
    )
    assert owner_read.status_code == 200, owner_read.text
    assert owner_read.json()["status"] == original_status


def test_refresh_uses_current_roles_after_role_change():
    from app.modules.authentication.api import tokens

    tenant_id = uuid4()
    email = f"v114-refresh-{uuid4().hex}@example.com"
    user = User.create(email, "V114 Refresh Role Test")
    users.save(user)
    credentials.register(user.id, "StrongPass123!")
    rbac.assign(user.id, "owner", tenant_id)

    login_response = client.post(
        "/auth/login",
        json={
            "email": email,
            "password": "StrongPass123!",
            "tenant_id": str(tenant_id),
        },
    )
    assert login_response.status_code == 200, login_response.text
    old_refresh = login_response.json()["refresh_token"]

    # Simulate revoking owner and retaining viewer.
    rbac.assignments[(user.id, tenant_id)] = {"viewer"}

    refresh_response = client.post(
        "/auth/refresh",
        json={"refresh_token": old_refresh},
    )
    assert refresh_response.status_code == 200, refresh_response.text

    new_access = refresh_response.json()["access_token"]
    record = tokens.validate(new_access)
    assert record.roles == ("viewer",)

    replay_response = client.post(
        "/auth/refresh",
        json={"refresh_token": old_refresh},
    )
    assert replay_response.status_code == 401


def test_refresh_rejects_user_after_all_tenant_roles_are_removed():
    from app.modules.authentication.api import tokens

    tenant_id = uuid4()
    email = f"v114-refresh-no-role-{uuid4().hex}@example.com"
    user = User.create(email, "V114 Refresh No Role Test")
    users.save(user)
    credentials.register(user.id, "StrongPass123!")
    rbac.assign(user.id, "owner", tenant_id)

    login_response = client.post(
        "/auth/login",
        json={
            "email": email,
            "password": "StrongPass123!",
            "tenant_id": str(tenant_id),
        },
    )
    assert login_response.status_code == 200, login_response.text
    old_refresh = login_response.json()["refresh_token"]

    # Remove every role assigned to this user in the tenant.
    rbac.assignments[(user.id, tenant_id)] = set()

    refresh_response = client.post(
        "/auth/refresh",
        json={"refresh_token": old_refresh},
    )
    assert refresh_response.status_code == 403, refresh_response.text

    # The rejected refresh token must not be usable again.
    replay_response = client.post(
        "/auth/refresh",
        json={"refresh_token": old_refresh},
    )
    assert replay_response.status_code == 401, replay_response.text

    from app.modules.authentication.security import TokenError, TokenType

    with __import__("pytest").raises(TokenError):
        tokens.validate(old_refresh, TokenType.REFRESH)


def test_invalid_decision_transition_preserves_status_and_version():
    from app.api.app import records

    tenant_id = uuid4()
    headers = _security_test_headers("owner", tenant_id)

    project = client.post(
        "/api/v1/projects",
        json={
            "organization_id": str(tenant_id),
            "name": f"Transition Test {uuid4().hex}",
        },
        headers=headers,
    )
    assert project.status_code == 200, project.text

    created = client.post(
        "/api/v1/decisions",
        json={
            "project_id": project.json()["id"],
            "title": "Invalid transition test",
            "objective": "Preserve decision state",
        },
        headers=headers,
    )
    assert created.status_code == 200, created.text

    decision_id = created.json()["id"]
    before = records.get("decisions", decision_id)
    assert before["status"] == "draft"
    assert before["version"] == 1

    response = client.post(
        f"/api/v1/decisions/{decision_id}/transition",
        params={"target": "approved"},
        headers=headers,
    )

    assert response.status_code == 422, response.text

    after = records.get("decisions", decision_id)
    assert after["status"] == before["status"]
    assert after["version"] == before["version"]


def test_guarded_project_command_rejects_missing_tenant_on_mutation():
    import pytest
    from uuid import uuid4
    from app.modules.project.application.commands import (
        CreateProject,
        ProjectCommandHandler,
        RenameProject,
    )
    from app.modules.project.application.repository import ProjectRepositoryAdapter
    from app.modules.project.application.tenant import ProjectTenantGuard
    from app.modules.project.persistence.sqlite import SQLiteProjectRepository

    backend = SQLiteProjectRepository()
    try:
        repository = ProjectRepositoryAdapter(backend)
        handler = ProjectCommandHandler(
            repository,
            tenant_guard=ProjectTenantGuard(),
        )
        tenant_id = uuid4()
        project = handler.create(
            CreateProject(
                organization_id=tenant_id,
                name="Tenant Guard Regression",
                tenant_id=tenant_id,
            )
        )

        with pytest.raises(PermissionError):
            handler.rename(
                RenameProject(
                    project_id=project.id,
                    new_name="Should Be Rejected",
                    tenant_id=None,
                )
            )

        unchanged = repository.get_by_id(project.id, tenant_id)
        assert unchanged.name == "Tenant Guard Regression"
    finally:
        backend.close()
