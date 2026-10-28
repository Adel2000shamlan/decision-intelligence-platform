"""Durable persistence for the legacy API resources.

This adapter intentionally uses api_* tables to avoid silently changing the
existing domain migration schema. Tenant scoping is a required follow-up before
these endpoints are considered production-safe.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from app.infrastructure.database import Database


class ApiRecordRepository:
    """Small DB-API-compatible JSON record repository with durable transactions."""

    _TABLES = {
        "organizations": "api_organizations",
        "projects": "api_projects",
        "decisions": "api_decisions",
        "risks": "api_risks",
    }

    def __init__(self, database: Database | None = None):
        self.database = database or Database()
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        with self.database.transaction() as conn:
            for table in self._TABLES.values():
                conn.execute(
                    f"""CREATE TABLE IF NOT EXISTS {table} (
                        id TEXT PRIMARY KEY,
                        payload TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    )"""
                )

    def _placeholder(self) -> str:
        return "?" if self.database.kind == "sqlite" else "%s"

    def add(self, kind: str, record: dict[str, Any]) -> dict[str, Any]:
        table = self._table(kind)
        now = datetime.now(timezone.utc).isoformat()
        payload = json.dumps(record, separators=(",", ":"), ensure_ascii=False)
        marker = self._placeholder()
        with self.database.transaction() as conn:
            conn.execute(
                f"INSERT INTO {table}(id,payload,created_at,updated_at) VALUES ({marker},{marker},{marker},{marker})",
                (str(record["id"]), payload, now, now),
            )
        return record

    def get(self, kind: str, record_id: str | UUID) -> dict[str, Any] | None:
        table = self._table(kind)
        marker = self._placeholder()
        with self.database.transaction() as conn:
            row = conn.execute(
                f"SELECT payload FROM {table} WHERE id={marker}", (str(record_id),)
            ).fetchone()
        if row is None:
            return None
        payload = row["payload"] if isinstance(row, sqlite3.Row) else row[0]
        return json.loads(payload)

    def list(self, kind: str) -> list[dict[str, Any]]:
        table = self._table(kind)
        with self.database.transaction() as conn:
            rows = conn.execute(
                f"SELECT payload FROM {table} ORDER BY created_at,id"
            ).fetchall()
        return [
            json.loads(row["payload"] if isinstance(row, sqlite3.Row) else row[0])
            for row in rows
        ]

    def update(self, kind: str, record: dict[str, Any]) -> dict[str, Any]:
        table = self._table(kind)
        now = datetime.now(timezone.utc).isoformat()
        marker = self._placeholder()
        payload = json.dumps(record, separators=(",", ":"), ensure_ascii=False)
        with self.database.transaction() as conn:
            cur = conn.execute(
                f"UPDATE {table} SET payload={marker},updated_at={marker} WHERE id={marker}",
                (payload, now, str(record["id"])),
            )
            if cur.rowcount != 1:
                raise KeyError(f"{kind} record not found")
        return record

    def _tenant_expression(self) -> str:
        if self.database.kind == "sqlite":
            return "json_extract(payload, '$.tenant_id')"
        return "(payload::jsonb ->> 'tenant_id')"

    def list_for_tenant(
        self, kind: str, tenant_id: str | UUID
    ) -> list[dict[str, Any]]:
        table = self._table(kind)
        marker = self._placeholder()
        tenant_expr = self._tenant_expression()
        with self.database.transaction() as conn:
            rows = conn.execute(
                f"SELECT payload FROM {table} "
                f"WHERE {tenant_expr}={marker} ORDER BY created_at,id",
                (str(tenant_id),),
            ).fetchall()
        return [
            json.loads(row["payload"] if isinstance(row, sqlite3.Row) else row[0])
            for row in rows
        ]

    def get_for_tenant(
        self, kind: str, record_id: str | UUID, tenant_id: str | UUID
    ) -> dict[str, Any] | None:
        table = self._table(kind)
        marker = self._placeholder()
        tenant_expr = self._tenant_expression()
        with self.database.transaction() as conn:
            row = conn.execute(
                f"SELECT payload FROM {table} "
                f"WHERE id={marker} AND {tenant_expr}={marker}",
                (str(record_id), str(tenant_id)),
            ).fetchone()
        if row is None:
            return None
        payload = row["payload"] if isinstance(row, sqlite3.Row) else row[0]
        return json.loads(payload)

    def update_for_tenant(
        self, kind: str, record: dict[str, Any], tenant_id: str | UUID
    ) -> dict[str, Any]:
        if str(record.get("tenant_id")) != str(tenant_id):
            raise KeyError(f"{kind} record not found")

        table = self._table(kind)
        marker = self._placeholder()
        tenant_expr = self._tenant_expression()
        now = datetime.now(timezone.utc).isoformat()
        payload = json.dumps(record, separators=(",", ":"), ensure_ascii=False)
        with self.database.transaction() as conn:
            cur = conn.execute(
                f"UPDATE {table} SET payload={marker},updated_at={marker} "
                f"WHERE id={marker} AND {tenant_expr}={marker}",
                (payload, now, str(record["id"]), str(tenant_id)),
            )
            if cur.rowcount != 1:
                raise KeyError(f"{kind} record not found")
        return record

    def _table(self, kind: str) -> str:
        try:
            return self._TABLES[kind]
        except KeyError as exc:
            raise ValueError(f"unsupported API resource: {kind}") from exc
