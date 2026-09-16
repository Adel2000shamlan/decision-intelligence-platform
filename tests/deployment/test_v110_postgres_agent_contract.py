from pathlib import Path
import os
import pytest
from uuid import uuid4

from app.modules.agent.domain.models import Agent
from app.modules.agent.persistence.postgres import PostgreSQLAgentRepository


def test_postgres_agent_repository_contract():
    source = Path(
        "app/modules/agent/persistence/postgres.py"
    ).read_text(encoding="utf-8")

    assert "class PostgreSQLAgentRepository" in source
    assert "import psycopg" in source
    assert "CREATE TABLE IF NOT EXISTS agents" in source
    assert "%s" in source
    assert "sqlite3" not in source


def test_agent_domain_uses_register_factory():
    agent = Agent.register(
        tenant_id="11111111-1111-1111-1111-111111111111",
        name="Contract Agent",
        capabilities={"research", "risk"},
    )

    assert agent.name == "Contract Agent"
    assert agent.capabilities == frozenset({"research", "risk"})
    assert agent.enabled is True


def test_postgres_agent_repository_round_trip():
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        pytest.skip("DATABASE_URL is required for PostgreSQL integration test")
    repo = PostgreSQLAgentRepository(dsn)

    agent = Agent.register(
        tenant_id="22222222-2222-2222-2222-222222222222",
        name=f"V110 Contract Agent {uuid4()}",
        capabilities={"research", "risk"},
    )

    repo.save(agent)
    loaded = repo.get(agent.id)

    assert loaded is not None
    assert loaded.id == agent.id
    assert loaded.tenant_id == agent.tenant_id
    assert loaded.capabilities == agent.capabilities

    disabled = agent.disable()
    repo.save(disabled)

    assert repo.get(agent.id).enabled is False
