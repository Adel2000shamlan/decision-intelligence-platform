from datetime import datetime
from uuid import UUID

import psycopg

from app.modules.knowledge.domain.models import KnowledgeItem


class PostgreSQLKnowledgeRepository:
    def __init__(self, dsn: str):
        self.dsn = dsn
        self._init_schema()

    def _connect(self):
        return psycopg.connect(self.dsn)

    def _init_schema(self):
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS knowledge_items (
                    id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    source TEXT NOT NULL,
                    project_id TEXT,
                    evidence_uri TEXT,
                    created_at TEXT NOT NULL,
                    version INTEGER NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_knowledge_tenant
                ON knowledge_items(tenant_id)
                """
            )

    def save(self, item: KnowledgeItem):
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO knowledge_items
                    (
                        id, tenant_id, title, content, source,
                        project_id, evidence_uri, created_at, version
                    )
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT(id) DO UPDATE SET
                    tenant_id=EXCLUDED.tenant_id,
                    title=EXCLUDED.title,
                    content=EXCLUDED.content,
                    source=EXCLUDED.source,
                    project_id=EXCLUDED.project_id,
                    evidence_uri=EXCLUDED.evidence_uri,
                    created_at=EXCLUDED.created_at,
                    version=EXCLUDED.version
                """,
                (
                    str(item.id),
                    str(item.tenant_id),
                    item.title,
                    item.content,
                    item.source,
                    str(item.project_id) if item.project_id else None,
                    item.evidence_uri,
                    item.created_at.isoformat(),
                    item.version,
                ),
            )
        return item

    def get(self, item_id):
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM knowledge_items WHERE id=%s",
                (str(item_id),),
            ).fetchone()
        return self._row(row) if row else None

    def list(self, tenant_id):
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM knowledge_items
                WHERE tenant_id=%s
                ORDER BY created_at
                """,
                (str(tenant_id),),
            ).fetchall()
        return [self._row(row) for row in rows]

    @staticmethod
    def _row(row):
        return KnowledgeItem(
            UUID(row[0]),
            UUID(row[1]),
            row[2],
            row[3],
            row[4],
            UUID(row[5]) if row[5] else None,
            row[6],
            datetime.fromisoformat(row[7]),
            row[8],
        )
