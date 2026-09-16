from uuid import UUID

import psycopg

from app.shared.domain.errors import BusinessRuleViolation

from ..domain.models import MemoryItem, MemoryStatus, MemoryType
from .repository import MemoryRepository


class PostgresMemoryRepository(MemoryRepository):
    def __init__(self, connection: psycopg.Connection):
        self.conn = connection
        self._init_schema()

    def _init_schema(self) -> None:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS memory_items (
                    id UUID PRIMARY KEY,
                    tenant_id UUID NOT NULL,
                    memory_type TEXT NOT NULL,
                    content TEXT NOT NULL,
                    source TEXT NOT NULL,
                    evidence_ids JSONB NOT NULL,
                    confidence DOUBLE PRECISION,
                    status TEXT NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL,
                    expires_at TIMESTAMPTZ,
                    version INTEGER NOT NULL
                )
                """
            )
            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_memory_tenant_created
                ON memory_items(tenant_id, created_at)
                """
            )
            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_memory_tenant_status
                ON memory_items(tenant_id, status)
                """
            )
        self.conn.commit()

    def save(self, item: MemoryItem) -> MemoryItem:
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO memory_items (
                        id, tenant_id, memory_type, content, source,
                        evidence_ids, confidence, status, created_at,
                        expires_at, version
                    )
                    VALUES (
                        %s, %s, %s, %s, %s,
                        %s::jsonb, %s, %s, %s,
                        %s, %s
                    )
                    ON CONFLICT(id) DO UPDATE SET
                        tenant_id=EXCLUDED.tenant_id,
                        memory_type=EXCLUDED.memory_type,
                        content=EXCLUDED.content,
                        source=EXCLUDED.source,
                        evidence_ids=EXCLUDED.evidence_ids,
                        confidence=EXCLUDED.confidence,
                        status=EXCLUDED.status,
                        created_at=EXCLUDED.created_at,
                        expires_at=EXCLUDED.expires_at,
                        version=EXCLUDED.version
                    """,
                    (
                        item.id,
                        item.tenant_id,
                        item.memory_type.value,
                        item.content,
                        item.source,
                        "[" + ",".join(
                            f'"{value}"' for value in item.evidence_ids
                        ) + "]",
                        item.confidence,
                        item.status.value,
                        item.created_at,
                        item.expires_at,
                        item.version,
                    ),
                )
            self.conn.commit()
        except psycopg.IntegrityError as exc:
            self.conn.rollback()
            raise BusinessRuleViolation(
                "memory item could not be saved"
            ) from exc
        return item

    def get(
        self,
        tenant_id: UUID,
        memory_id: UUID,
    ) -> MemoryItem | None:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    id, tenant_id, memory_type, content, source,
                    evidence_ids, confidence, status, created_at,
                    expires_at, version
                FROM memory_items
                WHERE tenant_id = %s AND id = %s
                """,
                (tenant_id, memory_id),
            )
            row = cur.fetchone()

        return self._row(row) if row else None

    def list(
        self,
        tenant_id: UUID,
        *,
        memory_type: MemoryType | None = None,
        status: MemoryStatus | None = None,
    ) -> tuple[MemoryItem, ...]:
        query = """
            SELECT
                id, tenant_id, memory_type, content, source,
                evidence_ids, confidence, status, created_at,
                expires_at, version
            FROM memory_items
            WHERE tenant_id = %s
        """
        params: list[object] = [tenant_id]

        if memory_type is not None:
            query += " AND memory_type = %s"
            params.append(MemoryType(memory_type).value)

        if status is not None:
            query += " AND status = %s"
            params.append(MemoryStatus(status).value)

        query += " ORDER BY created_at, id"

        with self.conn.cursor() as cur:
            cur.execute(query, params)
            rows = cur.fetchall()

        return tuple(self._row(row) for row in rows)

    def delete(self, tenant_id: UUID, memory_id: UUID) -> None:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                DELETE FROM memory_items
                WHERE tenant_id = %s AND id = %s
                """,
                (tenant_id, memory_id),
            )
        self.conn.commit()

    @staticmethod
    def _row(row) -> MemoryItem:
        evidence_ids = row[5] or []
        return MemoryItem(
            id=row[0],
            tenant_id=row[1],
            memory_type=MemoryType(row[2]),
            content=row[3],
            source=row[4],
            evidence_ids=tuple(UUID(value) for value in evidence_ids),
            confidence=row[6],
            status=MemoryStatus(row[7]),
            created_at=row[8],
            expires_at=row[9],
            version=row[10],
        )
