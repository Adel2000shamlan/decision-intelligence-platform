from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_main_app_exposes_official_decision_api():
    actor_id = uuid4()

    response = client.post(
        "/api/v1/official/decisions",
        json={
            "organization_id": str(uuid4()),
            "project_id": str(uuid4()),
            "title": "Main App Official Decision",
            "description": "Verify official decision API through main app",
            "actor_id": str(actor_id),
        },
    )

    assert response.status_code == 200

    result = response.json()
    assert result["status"] == "draft"
    assert result["version"] == 1
    assert result["title"] == "Main App Official Decision"

def test_main_app_integrates_official_organization_project_decision_risk():
    organization = client.post(
        "/api/v1/organizations",
        json={"name": "Integration Organization", "slug": f"integration-{uuid4().hex[:8]}"},
    )
    assert organization.status_code == 200
    organization_id = organization.json()["id"]

    project = client.post(
        "/api/v1/projects",
        json={
            "organization_id": organization_id,
            "name": "Integration Project",
        },
    )
    assert project.status_code == 200
    project_id = project.json()["id"]

    decision = client.post(
        "/api/v1/official/decisions",
        json={
            "organization_id": organization_id,
            "project_id": project_id,
            "title": "Integration Decision",
        },
    )
    assert decision.status_code == 200

    risk = client.post(
        "/api/v1/official/risks",
        json={
            "project_id": project_id,
            "title": "Integration Risk",
        },
    )
    assert risk.status_code == 200
    assert risk.json()["project_id"] == project_id
