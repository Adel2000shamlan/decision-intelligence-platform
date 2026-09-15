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
