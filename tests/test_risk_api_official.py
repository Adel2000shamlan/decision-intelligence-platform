from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_official_risk_full_lifecycle():
    project_id = uuid4()

    r = client.post(
        "/api/v1/official/risks",
        json={
            "project_id": str(project_id),
            "title": "Revenue decline",
            "description": "Demand may fall",
        },
    )
    assert r.status_code == 200
    risk = r.json()
    assert risk["project_id"] == str(project_id)
    assert risk["status"] == "draft"
    assert risk["version"] == 1

    risk_id = risk["id"]

    r = client.post(
        f"/api/v1/official/risks/{risk_id}/identify",
        json={"expected_version": 1},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "identified"
    assert r.json()["version"] == 2

    r = client.post(
        f"/api/v1/official/risks/{risk_id}/assess",
        json={"probability": 4, "impact": 4, "expected_version": 2},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "assessed"
    assert r.json()["score"] == 16
    assert r.json()["level"] == "high"
    assert r.json()["version"] == 3

    r = client.post(
        f"/api/v1/official/risks/{risk_id}/mitigation",
        json={"expected_version": 3},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "mitigating"
    assert r.json()["version"] == 4

    r = client.post(
        f"/api/v1/official/risks/{risk_id}/monitor",
        json={
            "residual_probability": 2,
            "residual_impact": 2,
            "expected_version": 4,
        },
    )
    assert r.status_code == 200
    assert r.json()["status"] == "monitored"
    assert r.json()["residual_score"] == 4
    assert r.json()["residual_level"] == "low"
    assert r.json()["version"] == 5

    r = client.post(
        f"/api/v1/official/risks/{risk_id}/accept",
        json={"expected_version": 5},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "accepted"
    assert r.json()["version"] == 6

    r = client.post(
        f"/api/v1/official/risks/{risk_id}/close",
        json={"expected_version": 6},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "closed"
    assert r.json()["version"] == 7

    r = client.post(
        f"/api/v1/official/risks/{risk_id}/archive",
        json={"expected_version": 7},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "archived"
    assert r.json()["version"] == 8


def test_official_risk_rejects_stale_version():
    project_id = uuid4()

    r = client.post(
        "/api/v1/official/risks",
        json={"project_id": str(project_id), "title": "Stale version risk"},
    )
    assert r.status_code == 200
    risk_id = r.json()["id"]

    r = client.post(
        f"/api/v1/official/risks/{risk_id}/identify",
        json={"expected_version": 1},
    )
    assert r.status_code == 200

    r = client.post(
        f"/api/v1/official/risks/{risk_id}/assess",
        json={"probability": 2, "impact": 2, "expected_version": 1},
    )
    assert r.status_code == 409
    assert "version" in r.json()["detail"].lower()


def test_official_risk_residual_guard():
    project_id = uuid4()

    r = client.post(
        "/api/v1/official/risks",
        json={"project_id": str(project_id), "title": "Residual guard risk"},
    )
    assert r.status_code == 200
    risk_id = r.json()["id"]

    assert client.post(
        f"/api/v1/official/risks/{risk_id}/identify",
        json={"expected_version": 1},
    ).status_code == 200

    assert client.post(
        f"/api/v1/official/risks/{risk_id}/assess",
        json={"probability": 2, "impact": 2, "expected_version": 2},
    ).status_code == 200

    assert client.post(
        f"/api/v1/official/risks/{risk_id}/mitigation",
        json={"expected_version": 3},
    ).status_code == 200

    r = client.post(
        f"/api/v1/official/risks/{risk_id}/monitor",
        json={
            "residual_probability": 5,
            "residual_impact": 5,
            "expected_version": 4,
        },
    )
    assert r.status_code == 409
    assert "residual risk" in r.json()["detail"].lower()
