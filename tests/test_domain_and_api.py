from uuid import uuid4

from fastapi.testclient import TestClient
from app.main import app
from app.modules.authentication.api import users, credentials, rbac
from app.modules.identity.domain.models import User
from app.shared.domain.state_machine import transition
from app.shared.domain.services import RiskScoreService

c = TestClient(app)


def authenticated_headers(tenant_id):
    email = f"api-{uuid4().hex}@example.com"
    user = User.create(email, "API Test User")
    users.save(user)
    credentials.register(user.id, "StrongPass123!")
    rbac.assign(user.id, "owner", tenant_id)
    response = c.post(
        "/auth/login",
        json={"email": email, "password": "StrongPass123!", "tenant_id": str(tenant_id)},
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_health():
    assert c.get("/api/v1/health").status_code == 200


def test_state():
    assert transition("decision", "draft", "validated") == "validated"


def test_risk():
    assert RiskScoreService().calculate(.5, 10) == 5


def test_flow():
    organization_id = uuid4()
    headers = authenticated_headers(organization_id)
    project_response = c.post(
        "/api/v1/projects",
        json={"organization_id": str(organization_id), "name": "Demo"},
        headers=headers,
    )
    assert project_response.status_code == 200, project_response.text
    project = project_response.json()
    assert "id" in project, project

    decision_response = c.post(
        "/api/v1/decisions",
        json={
            "project_id": project["id"],
            "title": "Choose",
            "objective": "Grow",
        },
        headers=headers,
    )
    assert decision_response.status_code == 200, decision_response.text

    risk_response = c.post(
        "/api/v1/risks",
        json={
            "project_id": project["id"],
            "title": "Cost",
            "probability": .4,
            "impact": 10,
        },
        headers=headers,
    )
    assert risk_response.status_code == 200, risk_response.text
    assert risk_response.json()["score"] == 4
