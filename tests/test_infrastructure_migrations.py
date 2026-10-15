import os
import sqlite3
import uuid

import pytest

from app.infrastructure.migrations import MIGRATION_ID, TABLES, apply_initial, rollback_initial


def test_initial_migration_is_idempotent_with_sqlite():
    conn = sqlite3.connect(":memory:")
    try:
        apply_initial(conn)
        apply_initial(conn)
        applied = conn.execute(
            "SELECT COUNT(*) FROM schema_migrations WHERE version = ?",
            (MIGRATION_ID,),
        ).fetchone()[0]
        assert applied == 1
        for table in TABLES:
            assert conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name = ?",
                (table,),
            ).fetchone() is not None
    finally:
        conn.close()


def test_initial_migration_can_be_rolled_back_with_sqlite():
    conn = sqlite3.connect(":memory:")
    try:
        apply_initial(conn)
        rollback_initial(conn)
        for table in TABLES:
            assert conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name = ?",
                (table,),
            ).fetchone() is None
        assert conn.execute(
            "SELECT 1 FROM schema_migrations WHERE version = ?",
            (MIGRATION_ID,),
        ).fetchone() is None
    finally:
        conn.close()


def test_initial_migration_is_idempotent_with_postgres():
    url = os.getenv("DATABASE_URL", "")
    if not url.startswith(("postgresql://", "postgres://", "postgresql+psycopg://")):
        pytest.skip("PostgreSQL integration test requires DATABASE_URL")

    psycopg = pytest.importorskip("psycopg")
    schema = "migration_test_" + uuid.uuid4().hex
    with psycopg.connect(url) as conn:
        conn.execute(f'CREATE SCHEMA "{schema}"')
        conn.execute("SELECT set_config('search_path', %s, false)", (schema,))
        try:
            apply_initial(conn)
            apply_initial(conn)
            applied = conn.execute(
                "SELECT COUNT(*) FROM schema_migrations WHERE version = %s",
                (MIGRATION_ID,),
            ).fetchone()[0]
            assert applied == 1
            for table in TABLES:
                assert conn.execute(
                    "SELECT to_regclass(%s)", (f"{schema}.{table}",)
                ).fetchone()[0] is not None
            rollback_initial(conn)
            for table in TABLES:
                assert conn.execute(
                    "SELECT to_regclass(%s)", (f"{schema}.{table}",)
                ).fetchone()[0] is None
        finally:
            conn.execute("SET search_path TO public")
            conn.execute(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE')
