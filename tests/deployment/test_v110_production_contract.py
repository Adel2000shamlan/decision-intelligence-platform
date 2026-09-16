from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_production_dockerfile_exists_and_runs_non_root():
    text = (ROOT / "Dockerfile.prod").read_text(encoding="utf-8")

    assert "FROM python:3.12-slim" in text
    assert "RUN useradd --create-home --uid 10001 appuser" in text
    assert "USER appuser" in text
    assert 'CMD ["python", "-m", "uvicorn", "app.main:app"' in text
    assert "pip install ." in text


def test_production_compose_externalizes_database_credentials():
    text = (ROOT / "docker-compose.prod.yml").read_text(encoding="utf-8")

    assert "postgres:" in text
    assert "redis:" in text
    assert "DATABASE_URL: postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}" in text
    assert "POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is required}" in text

    assert "POSTGRES_PASSWORD: password" not in text
    assert "postgresql://user:password@" not in text


def test_production_compose_has_service_healthchecks():
    text = (ROOT / "docker-compose.prod.yml").read_text(encoding="utf-8")

    assert "healthcheck:" in text
    assert "pg_isready" in text
    assert 'redis-cli", "ping"' in text
    assert "api/v1/health" in text
    assert "condition: service_healthy" in text


def test_production_compose_has_required_runtime_services():
    text = (ROOT / "docker-compose.prod.yml").read_text(encoding="utf-8")

    assert "services:" in text
    assert "api:" in text
    assert "postgres:" in text
    assert "redis:" in text
    assert 'ports:\n      - "8000:8000"' in text
