from __future__ import annotations

import sqlite3

import pytest

from app.infrastructure.database import Database


def test_sqlite_database_persists_committed_data_between_transactions(tmp_path):
    url = f"sqlite:///{tmp_path / 'durable.db'}"
    database = Database(url)

    with database.transaction() as conn:
        conn.execute("CREATE TABLE sample (id INTEGER PRIMARY KEY, value TEXT NOT NULL)")
        conn.execute("INSERT INTO sample(value) VALUES (?)", ("persisted",))

    with database.transaction() as conn:
        row = conn.execute("SELECT value FROM sample WHERE id = 1").fetchone()

    assert row == ("persisted",)


def test_sqlite_database_rolls_back_failed_transaction(tmp_path):
    database = Database(f"sqlite:///{tmp_path / 'rollback.db'}")
    with database.transaction() as conn:
        conn.execute("CREATE TABLE sample (id INTEGER PRIMARY KEY, value TEXT NOT NULL)")

    with pytest.raises(RuntimeError, match="force rollback"):
        with database.transaction() as conn:
            conn.execute("INSERT INTO sample(value) VALUES (?)", ("must-not-persist",))
            raise RuntimeError("force rollback")

    with database.transaction() as conn:
        count = conn.execute("SELECT COUNT(*) FROM sample").fetchone()[0]

    assert count == 0


def test_sqlite_database_enables_foreign_key_enforcement(tmp_path):
    database = Database(f"sqlite:///{tmp_path / 'foreign-keys.db'}")
    with database.transaction() as conn:
        conn.execute("CREATE TABLE parent (id INTEGER PRIMARY KEY)")
        conn.execute(
            "CREATE TABLE child (parent_id INTEGER NOT NULL REFERENCES parent(id))"
        )
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("INSERT INTO child(parent_id) VALUES (999)")
