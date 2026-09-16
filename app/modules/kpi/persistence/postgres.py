from datetime import datetime
from uuid import UUID

import psycopg

from app.modules.kpi.domain.models import KPI


class PostgreSQLKPIRepository:
    def __init__(self, dsn: str):
        self.dsn = dsn
        self._init_schema()

    def _connect(self):
        return psycopg.connect(self.dsn)

    def _init_schema(self):
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS kpis (
                    id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    unit TEXT NOT NULL,
                    target DOUBLE PRECISION NOT NULL,
                    actual DOUBLE PRECISION NOT NULL,
                    project_id TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    UNIQUE(tenant_id, name)
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_kpis_tenant
                ON kpis(tenant_id)
                """
            )

    def save(self, kpi: KPI):
        with self._connect() as conn:
            row = conn.execute(
                "SELECT version FROM kpis WHERE id=%s",
                (str(kpi.id),),
            ).fetchone()

            if row and row[0] != kpi.version - 1:
                raise RuntimeError("optimistic concurrency conflict")

            if row:
                conn.execute(
                    """
                    UPDATE kpis
                    SET
                        name=%s,
                        unit=%s,
                        target=%s,
                        actual=%s,
                        project_id=%s,
                        updated_at=%s,
                        version=%s
                    WHERE id=%s
                    """,
                    (
                        kpi.name,
                        kpi.unit,
                        kpi.target,
                        kpi.actual,
                        str(kpi.project_id) if kpi.project_id else None,
                        kpi.updated_at.isoformat(),
                        kpi.version,
                        str(kpi.id),
                    ),
                )
            else:
                conn.execute(
                    """
                    INSERT INTO kpis
                        (
                            id, tenant_id, name, unit, target,
                            actual, project_id, created_at,
                            updated_at, version
                        )
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    """,
                    (
                        str(kpi.id),
                        str(kpi.tenant_id),
                        kpi.name,
                        kpi.unit,
                        kpi.target,
                        kpi.actual,
                        str(kpi.project_id) if kpi.project_id else None,
                        kpi.created_at.isoformat(),
                        kpi.updated_at.isoformat(),
                        kpi.version,
                    ),
                )

        return kpi

    def get(self, kpi_id):
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM kpis WHERE id=%s",
                (str(kpi_id),),
            ).fetchone()

        return self._row(row) if row else None

    def list(self, tenant_id):
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM kpis
                WHERE tenant_id=%s
                ORDER BY created_at
                """,
                (str(tenant_id),),
            ).fetchall()

        return [self._row(row) for row in rows]

    @staticmethod
    def _row(row):
        return KPI(
            UUID(row[0]),
            UUID(row[1]),
            row[2],
            row[3],
            row[4],
            row[5],
            UUID(row[6]) if row[6] else None,
            datetime.fromisoformat(row[7]),
            datetime.fromisoformat(row[8]),
            row[9],
        )
