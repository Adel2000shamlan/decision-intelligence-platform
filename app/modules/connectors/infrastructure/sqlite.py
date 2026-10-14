from __future__ import annotations

import sqlite3
from datetime import datetime
from uuid import UUID

from app.modules.connectors.domain.models import (
    Connector,
    ConnectorKind,
    ConnectorStatus,
)
from app.shared.domain.errors import BusinessRuleViolation


class SQLiteConnectorRepository:
    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection
        self._initialize()

    def _initialize(self) -> None:
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS connectors (
                id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                name TEXT NOT NULL,
                kind TEXT NOT NULL,
                status TEXT NOT NULL,
                endpoint TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE (tenant_id, name)
            )
            """
        )
        self.connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_connectors_tenant
            ON connectors (tenant_id)
            """
        )
        self.connection.commit()

    def save(self, connector: Connector) -> None:
        try:
            self.connection.execute(
                """
                INSERT INTO connectors (
                    id,
                    tenant_id,
                    name,
                    kind,
                    status,
                    endpoint,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    tenant_id = excluded.tenant_id,
                    name = excluded.name,
                    kind = excluded.kind,
                    status = excluded.status,
                    endpoint = excluded.endpoint,
                    created_at = excluded.created_at
                """,
                (
                    str(connector.id),
                    str(connector.tenant_id),
                    connector.name,
                    connector.kind.value,
                    connector.status.value,
                    connector.endpoint,
                    connector.created_at.isoformat(),
                ),
            )
            self.connection.commit()
        except sqlite3.IntegrityError as exc:
            self.connection.rollback()
            raise BusinessRuleViolation(
                "connector name already exists for tenant"
            ) from exc

    def get(
        self,
        tenant_id: UUID,
        connector_id: UUID,
    ) -> Connector | None:
        row = self.connection.execute(
            """
            SELECT
                id,
                tenant_id,
                name,
                kind,
                status,
                endpoint,
                created_at
            FROM connectors
            WHERE tenant_id = ? AND id = ?
            """,
            (str(tenant_id), str(connector_id)),
        ).fetchone()

        return self._row(row) if row else None

    def list(self, tenant_id: UUID) -> tuple[Connector, ...]:
        rows = self.connection.execute(
            """
            SELECT
                id,
                tenant_id,
                name,
                kind,
                status,
                endpoint,
                created_at
            FROM connectors
            WHERE tenant_id = ?
            ORDER BY created_at, id
            """,
            (str(tenant_id),),
        ).fetchall()

        return tuple(self._row(row) for row in rows)

    def delete(
        self,
        tenant_id: UUID,
        connector_id: UUID,
    ) -> None:
        self.connection.execute(
            """
            DELETE FROM connectors
            WHERE tenant_id = ? AND id = ?
            """,
            (str(tenant_id), str(connector_id)),
        )
        self.connection.commit()

    @staticmethod
    def _row(row) -> Connector:
        return Connector(
            id=UUID(row[0]),
            tenant_id=UUID(row[1]),
            name=row[2],
            kind=ConnectorKind(row[3]),
            status=ConnectorStatus(row[4]),
            endpoint=row[5],
            created_at=datetime.fromisoformat(row[6]),
        )
