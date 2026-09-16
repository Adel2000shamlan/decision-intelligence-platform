import json
import sqlite3
from datetime import datetime
from uuid import UUID

from app.shared.domain.errors import BusinessRuleViolation

from ..domain.models import MemoryItem, MemoryStatus, MemoryType
from .repository import MemoryRepository


class SQLiteMemoryRepository(MemoryRepository):
    def __init__(self, connection: sqlite3.Connection | None = None):
        self.conn = connection or sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS memory_items (
                id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                memory_type TEXT NOT NULL,
                content TEXT NOT NULL,
                source TEXT NOT NULL,
                evidence_ids TEXT NOT NULL,
                confidence REAL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT,
                version INTEGER NOT NULL
            )
            """
        )
        self.conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_memory_tenant_created
            ON memory_items(tenant_id, created_at)
            """
        )
        self.conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_memory_tenant_status
            ON memory_items(tenant_id, status)
            """
        )
        self.conn.commit()

    def save(self, item: MemoryItem) -> MemoryItem:
        try:
            self.conn.execute(
                """
                INSERT INTO memory_items (
                    id, tenant_id, memory_type, content, source,
                    evidence_ids, confidence, status, created_at,
                    expires_at, version
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    tenant_id=excluded.tenant_id,
                    memory_type=excluded.memory_type,
                    content=excluded.content,
                    source=excluded.source,
                    evidence_ids=excluded.evidence_ids,
                    confidence=excluded.confidence,
                    status=excluded.status,
                    created_at=excluded.created_at,
                    expires_at=excluded.expires_at,
                    version=excluded.version
                """,
                (
                    str(item.id),
                    str(item.tenant_id),
                    item.memory_type.value,
                    item.content,
                    item.source,
                    json.dumps([str(value) for value in item.evidence_ids]),
                    item.confidence,
                    item.status.value,
                    item.created_at.isoformat(),
                    item.expires_at.isoformat() if item.expires_at else None,
                    item.version,
                ),
            )
            self.conn.commit()
        except sqlite3.IntegrityError as exc:
            raise BusinessRuleViolation(
                "memory item could not be saved"
            ) from exc
        return item

    def get(
        self,
        tenant_id: UUID,
        memory_id: UUID,
    ) -> MemoryItem | None:
        row = self.conn.execute(
            """
            SELECT * FROM memory_items
            WHERE tenant_id = ? AND id = ?
            """,
            (str(tenant_id), str(memory_id)),
        ).fetchone()
        return self._row(row) if row else None

    def list(
        self,
        tenant_id: UUID,
        *,
        memory_type: MemoryType | None = None,
        status: MemoryStatus | None = None,
    ) -> tuple[MemoryItem, ...]:
        query = """
            SELECT * FROM memory_items
            WHERE tenant_id = ?
        """
        params: list[str] = [str(tenant_id)]

        if memory_type is not None:
            query += " AND memory_type = ?"
            params.append(MemoryType(memory_type).value)

        if status is not None:
            query += " AND status = ?"
            params.append(MemoryStatus(status).value)

        query += " ORDER BY created_at, id"

        rows = self.conn.execute(query, params).fetchall()
        return tuple(self._row(row) for row in rows)

    def delete(self, tenant_id: UUID, memory_id: UUID) -> None:
        self.conn.execute(
            """
            DELETE FROM memory_items
            WHERE tenant_id = ? AND id = ?
            """,
            (str(tenant_id), str(memory_id)),
        )
        self.conn.commit()

    @staticmethod
    def _row(row: sqlite3.Row) -> MemoryItem:
        return MemoryItem(
            id=UUID(row["id"]),
            tenant_id=UUID(row["tenant_id"]),
            memory_type=MemoryType(row["memory_type"]),
            content=row["content"],
            source=row["source"],
            evidence_ids=tuple(
                UUID(value) for value in json.loads(row["evidence_ids"])
            ),
            confidence=row["confidence"],
            status=MemoryStatus(row["status"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            expires_at=(
                datetime.fromisoformat(row["expires_at"])
                if row["expires_at"]
                else None
            ),
            version=row["version"],
        )
