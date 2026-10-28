from types import SimpleNamespace
from uuid import uuid4

from fastapi.testclient import TestClient

import app.infrastructure.config as config
from app.main import app
from app.modules.authentication.api import password_resets

client = TestClient(app)


def test_reset_request_exposes_token_in_development_only(monkeypatch):
    expected_token = "test-only-reset-token"
    original_request = password_resets.request

    try:
        password_resets.request = lambda user_id: expected_token

        monkeypatch.setattr(
            config, "settings", SimpleNamespace(environment="development")
        )
        development_response = client.post(
            "/auth/password-reset/request",
            json={"user_id": str(uuid4())},
        )
        assert development_response.status_code == 200
        assert development_response.json() == {
            "accepted": True,
            "reset_token": expected_token,
        }

        monkeypatch.setattr(
            config, "settings", SimpleNamespace(environment="production")
        )
        production_response = client.post(
            "/auth/password-reset/request",
            json={"user_id": str(uuid4())},
        )
        assert production_response.status_code == 200
        assert production_response.json() == {"accepted": True}
        assert "reset_token" not in production_response.json()
    finally:
        password_resets.request = original_request
