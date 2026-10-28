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
    database = Database(DATABASE_URL)
    repository = ApiRecordRepository(database)
    record_id = str(uuid4())

    try:
        original = {
            "id": record_id,
            "name": "integration-" + record_id,
            "status": "active",
            "version": 1,
        }
        repository.add("organizations", original)

        independent_repository = ApiRecordRepository(Database(DATABASE_URL))
        assert independent_repository.get("organizations", record_id) == original

        updated = {
            **original,
            "name": original["name"] + "-updated",
            "version": 2,
        }
        independent_repository.update("organizations", updated)

        assert ApiRecordRepository(Database(DATABASE_URL)).get(
            "organizations", record_id
        ) == updated
    finally:
        with database.transaction() as connection:
            connection.execute(
                "DELETE FROM api_organizations WHERE id = %s",
                (record_id,),
            )


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

@requires_postgres
def test_postgres_api_records_are_isolated_by_tenant():
    database = Database(DATABASE_URL)
    repository = ApiRecordRepository(database)
    tenant_a = str(uuid4())
    tenant_b = str(uuid4())
    record_a_id = str(uuid4())
    record_b_id = str(uuid4())

    record_a = {
        "id": record_a_id,
        "tenant_id": tenant_a,
        "name": "tenant-a",
        "status": "active",
        "version": 1,
    }
    record_b = {
        "id": record_b_id,
        "tenant_id": tenant_b,
        "name": "tenant-b",
        "status": "active",
        "version": 1,
    }

    try:
        repository.add("organizations", record_a)
        repository.add("organizations", record_b)

        assert repository.list_for_tenant("organizations", tenant_a) == [record_a]
        assert repository.get_for_tenant(
            "organizations", record_b_id, tenant_a
        ) is None

        spoofed_record = {
            **record_b,
            "tenant_id": tenant_a,
            "name": "cross-tenant-overwrite",
        }
        with pytest.raises(KeyError):
            repository.update_for_tenant(
                "organizations", spoofed_record, tenant_a
            )

        assert repository.get_for_tenant(
            "organizations", record_b_id, tenant_b
        ) == record_b
    finally:
        with database.transaction() as connection:
            connection.execute(
                "DELETE FROM api_organizations WHERE id = %s",
                (record_a_id,),
            )
            connection.execute(
                "DELETE FROM api_organizations WHERE id = %s",
                (record_b_id,),
            )
