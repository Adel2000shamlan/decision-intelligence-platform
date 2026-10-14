import os
import subprocess
import sys


def _run_settings(**environment):
    env = os.environ.copy()
    env.update(environment)
    return subprocess.run(
        [
            sys.executable,
            "-c",
            "from app.infrastructure.config import Settings; Settings(); print('SETTINGS_OK')",
        ],
        env=env,
        capture_output=True,
        text=True,
    )


def test_production_rejects_sqlite_database_url():
    result = _run_settings(
        APP_ENV="production",
        DATABASE_URL="sqlite:///./decision_intelligence.db",
    )

    assert result.returncode != 0
    assert "Production requires a PostgreSQL DATABASE_URL" in result.stderr


def test_production_rejects_missing_database_url():
    env = os.environ.copy()
    env.pop("DATABASE_URL", None)
    env["APP_ENV"] = "production"

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from app.infrastructure.config import Settings; Settings(); print('SETTINGS_OK')",
        ],
        env=env,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "Production requires a PostgreSQL DATABASE_URL" in result.stderr


def test_production_accepts_postgresql_database_url():
    result = _run_settings(
        APP_ENV="production",
        DATABASE_URL="postgresql://user:password@localhost:5432/decision_intelligence",
    )

    assert result.returncode == 0
    assert "SETTINGS_OK" in result.stdout


def test_development_allows_default_sqlite_database():
    env = os.environ.copy()
    env.pop("DATABASE_URL", None)
    env["APP_ENV"] = "development"

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from app.infrastructure.config import Settings; Settings(); print(Settings().database_url)",
        ],
        env=env,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "sqlite:///" in result.stdout


def test_health_route_is_unique_in_openapi():
    from app.main import app

    schema = app.openapi()

    health_paths = [
        path for path in schema["paths"]
        if path == "/api/v1/health"
    ]

    assert health_paths == ["/api/v1/health"]
    assert sorted(schema["paths"]["/api/v1/health"]) == ["get"]


def test_import_does_not_leave_unclosed_sqlite_connections():
    result = subprocess.run(
        [
            sys.executable,
            "-W",
            "error::ResourceWarning",
            "-c",
            "from app.main import app; app.openapi()",
        ],
        env=os.environ.copy(),
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
