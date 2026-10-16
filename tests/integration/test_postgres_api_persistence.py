"""PostgreSQL integration acceptance tests for durable API record storage.

These tests run against the real PostgreSQL service configured by CI. They are
skipped only when a local developer has not configured DATABASE_URL to PostgreSQL.
They deliberately use unique identifiers so a shared test database remains safe.
"""
from __future__ import annotations

import os
from uuid import uuid4

import pytest

from app.infrastructure.database import Database
from app.infrastructure.api_repository import ApiRecordRepository


DATABASE_URL = os.getenv("DATABASE_URL", "")
requires_postgres = pytest.mark.skipif(
    not DATABASE_URL.startswith(("postgresql://", "postgres://")),
    reason="requires a real PostgreSQL DATABASE_URL",
)


@requires_postgres
def test_postgres_api_record_create_update_read_across_repository_instances():
    repository = ApiRecordRepository(Database(DATABASE_URL))
    record_id = str(uuid4())
    original = {
        "id": record_id,
        "name": "integration-" + record_id,
        "status": "active",
        "version": 1,
    }
    repository.add("organizations", original)

    independent_repository = ApiRecordRepository(Database(DATABASE_URL))
    assert independent_repository.get("organizations", record_id) == original

    updated = {**original, "name": original["name"] + "-updated", "version": 2}
    independent_repository.update("organizations", updated)
    assert ApiRecordRepository(Database(DATABASE_URL)).get(
        "organizations", record_id
    ) == updated


@requires_postgres
def test_postgres_database_transaction_rolls_back_on_exception():
    database = Database(DATABASE_URL)
    table = "integration_rollback_" + uuid4().hex
    with database.transaction() as connection:
        connection.execute(
            f"CREATE TABLE {table} (id TEXT PRIMARY KEY, value TEXT NOT NULL)"
        )

    with pytest.raises(RuntimeError, match="force rollback"):
        with database.transaction() as connection:
            marker = "%s"
            connection.execute(
                f"INSERT INTO {table}(id, value) VALUES ({marker}, {marker})",
                ("one", "must-not-commit"),
            )
            raise RuntimeError("force rollback")

    with database.transaction() as connection:
        row = connection.execute(f"SELECT id FROM {table}").fetchone()
        connection.execute(f"DROP TABLE {table}")
    assert row is None


@requires_postgres
def test_postgres_repository_rejects_unknown_resource():
    repository = ApiRecordRepository(Database(DATABASE_URL))
    with pytest.raises(ValueError, match="unsupported API resource"):
        repository.list("users")
