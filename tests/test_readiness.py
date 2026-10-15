from fastapi.testclient import TestClient
import pytest

from app.main import app

client = TestClient(app)


def test_readiness_returns_503_when_production_dependencies_are_not_configured(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("REDIS_URL", raising=False)

    response = client.get("/api/v1/ready")

    assert response.status_code == 503
    assert response.json()["detail"] == {
        "status": "not_ready",
        "checks": {"database": "error", "redis": "error"},
    }


def test_readiness_returns_ready_when_postgres_and_redis_are_healthy(monkeypatch):
    class FakeConnection:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def execute(self, query):
            assert query == "SELECT 1"

    class FakeDatabase:
        def __init__(self, url):
            assert url == "postgresql://example"

        def transaction(self):
            return FakeConnection()

    class FakeRedis:
        def ping(self):
            return True

        def close(self):
            pass

    class FakeRedisFactory:
        @staticmethod
        def from_url(url, **kwargs):
            assert url == "redis://example"
            return FakeRedis()

    monkeypatch.setenv("DATABASE_URL", "postgresql://example")
    monkeypatch.setenv("REDIS_URL", "redis://example")
    monkeypatch.setattr("app.api.app.Database", FakeDatabase)
    import redis
    monkeypatch.setattr(redis, "Redis", FakeRedisFactory)

    response = client.get("/api/v1/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "checks": {"database": "ok", "redis": "ok"},
    }


def test_readiness_returns_503_when_a_dependency_fails(monkeypatch):
    class FailedDatabase:
        def __init__(self, url):
            pass

        def transaction(self):
            raise ConnectionError("unavailable")

    class FakeRedis:
        def ping(self):
            return True

        def close(self):
            pass

    class FakeRedisFactory:
        @staticmethod
        def from_url(url, **kwargs):
            return FakeRedis()

    monkeypatch.setenv("DATABASE_URL", "postgresql://example")
    monkeypatch.setenv("REDIS_URL", "redis://example")
    monkeypatch.setattr("app.api.app.Database", FailedDatabase)
    import redis
    monkeypatch.setattr(redis, "Redis", FakeRedisFactory)

    response = client.get("/api/v1/ready")

    assert response.status_code == 503
    assert response.json()["detail"]["checks"] == {
        "database": "error",
        "redis": "ok",
    }
