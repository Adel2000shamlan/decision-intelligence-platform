from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app


def create_organization(client):
    response = client.post(
        "/api/v1/organizations",
        json={
            "name": f"BA API Test Organization {uuid4()}",
            "slug": f"ba-api-test-{uuid4().hex[:12]}",
        },
    )
    assert response.status_code == 200
    return response.json()


def create_assessment(client, organization_id):
    response = client.post(
        "/api/v1/business-assessments",
        json={
            "organization_id": organization_id,
            "title": f"Business Assessment {uuid4()}",
            "idea_description": "API integration test",
            "actor_id": organization_id,
            "tenant_id": organization_id,
        },
    )
    assert response.status_code == 200
    return response.json()


def test_business_assessment_api_create_and_get():
    with TestClient(app) as client:
        organization = create_organization(client)
        assessment = create_assessment(client, organization["id"])

        assert assessment["organization_id"] == organization["id"]
        assert assessment["status"] == "draft"
        assert assessment["version"] == 1

        response = client.get(
            f"/api/v1/business-assessments/{assessment['id']}"
            f"?tenant_id={organization['id']}"
        )

        assert response.status_code == 200
        assert response.json()["id"] == assessment["id"]
        assert response.json()["status"] == "draft"


def test_business_assessment_api_lifecycle_to_data_collection():
    with TestClient(app) as client:
        organization = create_organization(client)
        assessment = create_assessment(client, organization["id"])

        response = client.post(
            f"/api/v1/business-assessments/{assessment['id']}/data-collection",
            json={
                "actor_id": organization["id"],
                "tenant_id": organization["id"],
                "expected_version": 1,
            },
        )

        assert response.status_code == 200
        body = response.json()

        assert body["id"] == assessment["id"]
        assert body["status"] == "data_collection"
        assert body["version"] == 2


def test_business_assessment_api_rejects_cross_tenant_access():
    with TestClient(app) as client:
        organization = create_organization(client)
        assessment = create_assessment(client, organization["id"])
        wrong_tenant = str(uuid4())

        response = client.post(
            f"/api/v1/business-assessments/{assessment['id']}/data-collection",
            json={
                "actor_id": wrong_tenant,
                "tenant_id": wrong_tenant,
                "expected_version": 1,
            },
        )

        assert response.status_code == 403
        assert "tenant boundary" in response.json()["detail"]


def test_business_assessment_api_lists_by_organization_and_status():
    with TestClient(app) as client:
        organization = create_organization(client)
        assessment = create_assessment(client, organization["id"])

        response = client.get(
            f"/api/v1/business-assessments/organization/{organization['id']}"
            f"?tenant_id={organization['id']}"
        )

        assert response.status_code == 200
        body = response.json()

        assert len(body) == 1
        assert body[0]["id"] == assessment["id"]

        response = client.get(
            f"/api/v1/business-assessments/organization/"
            f"{organization['id']}/status/draft"
            f"?tenant_id={organization['id']}"
        )

        assert response.status_code == 200
        body = response.json()

        assert len(body) == 1
        assert body[0]["id"] == assessment["id"]
        assert body[0]["status"] == "draft"
