from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.modules.decision.api.router import router


app = FastAPI()
app.include_router(router, prefix="/api/v1")

client = TestClient(app)


def test_official_decision_lifecycle_and_versioning():
    organization_id = uuid4()
    project_id = uuid4()
    actor_id = uuid4()

    response = client.post(
        "/api/v1/decisions",
        json={
            "organization_id": str(organization_id),
            "project_id": str(project_id),
            "title": "Official Decision",
            "description": "Verify official API lifecycle",
            "actor_id": str(actor_id),
        },
    )

    assert response.status_code == 200
    decision = response.json()
    decision_id = decision["id"]

    assert decision["status"] == "draft"
    assert decision["version"] == 1

    response = client.post(
        f"/api/v1/decisions/{decision_id}/analysis",
        json={"expected_version": 1, "actor_id": str(actor_id)},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "analysis"
    assert response.json()["version"] == 2

    response = client.post(
        f"/api/v1/decisions/{decision_id}/submit",
        json={"expected_version": 2, "actor_id": str(actor_id)},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "ready_for_approval"
    assert response.json()["version"] == 3

    response = client.post(
        f"/api/v1/decisions/{decision_id}/approve",
        json={"expected_version": 3, "actor_id": str(actor_id)},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "approved"
    assert response.json()["version"] == 4

    stale = client.post(
        f"/api/v1/decisions/{decision_id}/execute",
        json={"expected_version": 3, "actor_id": str(actor_id)},
    )
    assert stale.status_code == 409

    current = client.get(f"/api/v1/decisions/{decision_id}")
    assert current.status_code == 200
    assert current.json()["status"] == "approved"
    assert current.json()["version"] == 4
