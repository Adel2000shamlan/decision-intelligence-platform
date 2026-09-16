import sqlite3
from uuid import UUID

from app.shared.domain.errors import BusinessRuleViolation, InvalidDomainData

from ..domain.models import KnowledgeEdge, KnowledgeNode
from .repository import KnowledgeGraphRepository


class SQLiteKnowledgeGraphRepository(KnowledgeGraphRepository):
    def __init__(self, connection: sqlite3.Connection):
        self._connection = connection
        self._connection.row_factory = sqlite3.Row
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        self._connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS knowledge_graph_nodes (
                id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                node_type TEXT NOT NULL,
                label TEXT NOT NULL,
                source TEXT NOT NULL,
                source_uri TEXT,
                created_at TEXT NOT NULL
            );

            CREATE UNIQUE INDEX IF NOT EXISTS uq_knowledge_graph_nodes_identity
            ON knowledge_graph_nodes (
                tenant_id,
                node_type,
                label,
                source,
                COALESCE(source_uri, '')
            );

            CREATE TABLE IF NOT EXISTS knowledge_graph_edges (
                id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                source_node_id TEXT NOT NULL,
                target_node_id TEXT NOT NULL,
                relation_type TEXT NOT NULL,
                source TEXT NOT NULL,
                confidence REAL,
                created_at TEXT NOT NULL,
                UNIQUE (
                    tenant_id,
                    source_node_id,
                    target_node_id,
                    relation_type
                ),
                FOREIGN KEY (source_node_id)
                    REFERENCES knowledge_graph_nodes(id)
                    ON DELETE CASCADE,
                FOREIGN KEY (target_node_id)
                    REFERENCES knowledge_graph_nodes(id)
                    ON DELETE CASCADE
            );
            """
        )
        self._connection.commit()

    def add_node(self, node: KnowledgeNode) -> KnowledgeNode:
        try:
            self._connection.execute(
                """
                INSERT INTO knowledge_graph_nodes
                (id, tenant_id, node_type, label, source, source_uri, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(node.id),
                    str(node.tenant_id),
                    node.node_type.value,
                    node.label,
                    node.source,
                    node.source_uri,
                    node.created_at.isoformat(),
                ),
            )
            self._connection.commit()
        except sqlite3.IntegrityError as exc:
            raise BusinessRuleViolation(
                "duplicate knowledge node"
            ) from exc

        return node

    def add_edge(self, edge: KnowledgeEdge) -> KnowledgeEdge:
        source = self.get_node(edge.tenant_id, edge.source_node_id)
        target = self.get_node(edge.tenant_id, edge.target_node_id)

        if source is None:
            raise BusinessRuleViolation("source node does not exist")
        if target is None:
            raise BusinessRuleViolation("target node does not exist")

        try:
            self._connection.execute(
                """
                INSERT INTO knowledge_graph_edges
                (
                    id, tenant_id, source_node_id, target_node_id,
                    relation_type, source, confidence, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(edge.id),
                    str(edge.tenant_id),
                    str(edge.source_node_id),
                    str(edge.target_node_id),
                    edge.relation_type.value,
                    edge.source,
                    edge.confidence,
                    edge.created_at.isoformat(),
                ),
            )
            self._connection.commit()
        except sqlite3.IntegrityError as exc:
            raise BusinessRuleViolation(
                "duplicate knowledge edge"
            ) from exc

        return edge

    def get_node(self, tenant_id: UUID, node_id: UUID) -> KnowledgeNode | None:
        row = self._connection.execute(
            """
            SELECT *
            FROM knowledge_graph_nodes
            WHERE tenant_id = ? AND id = ?
            """,
            (str(tenant_id), str(node_id)),
        ).fetchone()

        if row is None:
            return None

        return KnowledgeNode(
            id=UUID(row["id"]),
            tenant_id=UUID(row["tenant_id"]),
            node_type=row["node_type"],
            label=row["label"],
            source=row["source"],
            source_uri=row["source_uri"],
            created_at=__import__("datetime").datetime.fromisoformat(
                row["created_at"]
            ),
        )

    def get_edge(self, tenant_id: UUID, edge_id: UUID) -> KnowledgeEdge | None:
        row = self._connection.execute(
            """
            SELECT *
            FROM knowledge_graph_edges
            WHERE tenant_id = ? AND id = ?
            """,
            (str(tenant_id), str(edge_id)),
        ).fetchone()

        if row is None:
            return None

        return KnowledgeEdge(
            id=UUID(row["id"]),
            tenant_id=UUID(row["tenant_id"]),
            source_node_id=UUID(row["source_node_id"]),
            target_node_id=UUID(row["target_node_id"]),
            relation_type=row["relation_type"],
            source=row["source"],
            confidence=row["confidence"],
            created_at=__import__("datetime").datetime.fromisoformat(
                row["created_at"]
            ),
        )

    def list_nodes(self, tenant_id: UUID) -> tuple[KnowledgeNode, ...]:
        rows = self._connection.execute(
            """
            SELECT *
            FROM knowledge_graph_nodes
            WHERE tenant_id = ?
            ORDER BY created_at, id
            """,
            (str(tenant_id),),
        ).fetchall()

        return tuple(
            self.get_node(tenant_id, UUID(row["id"]))
            for row in rows
        )

    def list_edges(self, tenant_id: UUID) -> tuple[KnowledgeEdge, ...]:
        rows = self._connection.execute(
            """
            SELECT *
            FROM knowledge_graph_edges
            WHERE tenant_id = ?
            ORDER BY created_at, id
            """,
            (str(tenant_id),),
        ).fetchall()

        return tuple(
            self.get_edge(tenant_id, UUID(row["id"]))
            for row in rows
        )

    def delete_node(self, tenant_id: UUID, node_id: UUID) -> None:
        self._connection.execute(
            """
            DELETE FROM knowledge_graph_nodes
            WHERE tenant_id = ? AND id = ?
            """,
            (str(tenant_id), str(node_id)),
        )
        self._connection.commit()

    def delete_edge(self, tenant_id: UUID, edge_id: UUID) -> None:
        self._connection.execute(
            """
            DELETE FROM knowledge_graph_edges
            WHERE tenant_id = ? AND id = ?
            """,
            (str(tenant_id), str(edge_id)),
        )
        self._connection.commit()
