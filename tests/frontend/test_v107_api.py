from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_v107_frontend_index_is_served():
    response = client.get("/api/v1/frontend/")

    assert response.status_code == 200
    assert "Decision Intelligence Platform" in response.text
    assert 'id="app"' in response.text


def test_v107_frontend_manifest_is_served():
    response = client.get("/api/v1/frontend/manifest.webmanifest")

    assert response.status_code == 200
    assert response.json()["name"] == "Decision Intelligence Platform"


def test_v107_frontend_app_js_is_served():
    response = client.get("/api/v1/frontend/app.js")

    assert response.status_code == 200
    assert "Decision Intelligence Platform" in response.text


def test_v107_frontend_styles_are_served():
    response = client.get("/api/v1/frontend/styles.css")

    assert response.status_code == 200
    assert ".shell" in response.text


def test_v107_frontend_service_worker_is_served():
    response = client.get("/api/v1/frontend/service-worker.js")

    assert response.status_code == 200
    assert "CACHE_NAME" in response.text


def test_v107_frontend_content_types():
    expected = {
        "/api/v1/frontend/": "text/html",
        "/api/v1/frontend/index.html": "text/html",
        "/api/v1/frontend/manifest.webmanifest": "application/manifest+json",
        "/api/v1/frontend/app.js": "text/javascript",
        "/api/v1/frontend/styles.css": "text/css",
        "/api/v1/frontend/service-worker.js": "text/javascript",
    }

    for path, content_type in expected.items():
        response = client.get(path)
        assert response.status_code == 200
        assert response.headers["content-type"].startswith(content_type)
