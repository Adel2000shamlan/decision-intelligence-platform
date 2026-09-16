from datetime import datetime
from uuid import UUID

import psycopg

from app.modules.agent.domain.models import Agent


class PostgreSQLAgentRepository:
    def __init__(self, dsn: str):
        self.dsn = dsn
        self._init_schema()

    def _connect(self):
        return psycopg.connect(self.dsn)

    def _init_schema(self):
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS agents (
                    id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    capabilities TEXT NOT NULL,
                    enabled INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(tenant_id, name)
                )
                """
            )

    def save(self, agent):
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO agents
                    (id, tenant_id, name, capabilities, enabled, created_at)
                VALUES (%s,%s,%s,%s,%s,%s)
                ON CONFLICT(id) DO UPDATE SET
                    tenant_id=EXCLUDED.tenant_id,
                    name=EXCLUDED.name,
                    capabilities=EXCLUDED.capabilities,
                    enabled=EXCLUDED.enabled,
                    created_at=EXCLUDED.created_at
                """,
                (
                    str(agent.id),
                    str(agent.tenant_id),
                    agent.name,
                    ",".join(sorted(agent.capabilities)),
                    int(agent.enabled),
                    agent.created_at.isoformat(),
                ),
            )

        return agent

    def get(self, agent_id):
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM agents WHERE id=%s",
                (str(agent_id),),
            ).fetchone()

        return self._row(row) if row else None

    def list(self, tenant_id):
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM agents
                WHERE tenant_id=%s
                ORDER BY created_at, id
                """,
                (str(tenant_id),),
            ).fetchall()

        return [self._row(row) for row in rows]

    @staticmethod
    def _row(row):
        return Agent(
            UUID(row[0]),
            UUID(row[1]),
            row[2],
            frozenset(filter(None, row[3].split(","))),
            bool(row[4]),
            datetime.fromisoformat(row[5]),
        )
