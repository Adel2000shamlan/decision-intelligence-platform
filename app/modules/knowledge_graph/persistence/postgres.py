from uuid import UUID

import psycopg
from psycopg.rows import dict_row

from app.shared.domain.errors import BusinessRuleViolation

from ..domain.models import KnowledgeEdge, KnowledgeNode
from .mappers import edge_from_row, edge_to_row, node_from_row, node_to_row
from .repository import KnowledgeGraphRepository


class PostgresKnowledgeGraphRepository(KnowledgeGraphRepository):
    def __init__(self, connection: psycopg.Connection):
        self._connection = connection
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS knowledge_graph_nodes (
                    id UUID PRIMARY KEY,
                    tenant_id UUID NOT NULL,
                    node_type TEXT NOT NULL,
                    label TEXT NOT NULL,
                    source TEXT NOT NULL,
                    source_uri TEXT,
                    created_at TIMESTAMPTZ NOT NULL
                );

                CREATE UNIQUE INDEX IF NOT EXISTS
                uq_knowledge_graph_nodes_identity
                ON knowledge_graph_nodes (
                    tenant_id,
                    node_type,
                    label,
                    source,
                    COALESCE(source_uri, '')
                );

                CREATE TABLE IF NOT EXISTS knowledge_graph_edges (
                    id UUID PRIMARY KEY,
                    tenant_id UUID NOT NULL,
                    source_node_id UUID NOT NULL,
                    target_node_id UUID NOT NULL,
                    relation_type TEXT NOT NULL,
                    source TEXT NOT NULL,
                    confidence DOUBLE PRECISION,
                    created_at TIMESTAMPTZ NOT NULL,
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
            with self._connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO knowledge_graph_nodes
                    (
                        id, tenant_id, node_type, label,
                        source, source_uri, created_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    node_to_row(node),
                )
            self._connection.commit()
        except psycopg.IntegrityError as exc:
            self._connection.rollback()
            raise BusinessRuleViolation(
                "duplicate knowledge node"
            ) from exc
        return node

    def add_edge(self, edge: KnowledgeEdge) -> KnowledgeEdge:
        if self.get_node(edge.tenant_id, edge.source_node_id) is None:
            raise BusinessRuleViolation("source node does not exist")

        if self.get_node(edge.tenant_id, edge.target_node_id) is None:
            raise BusinessRuleViolation("target node does not exist")

        try:
            with self._connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO knowledge_graph_edges
                    (
                        id, tenant_id, source_node_id, target_node_id,
                        relation_type, source, confidence, created_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    edge_to_row(edge),
                )
            self._connection.commit()
        except psycopg.IntegrityError as exc:
            self._connection.rollback()
            raise BusinessRuleViolation(
                "duplicate knowledge edge"
            ) from exc
        return edge

    def get_node(
        self,
        tenant_id: UUID,
        node_id: UUID,
    ) -> KnowledgeNode | None:
        with self._connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                SELECT *
                FROM knowledge_graph_nodes
                WHERE tenant_id = %s AND id = %s
                """,
                (tenant_id, node_id),
            )
            row = cursor.fetchone()

        return None if row is None else node_from_row(row)

    def get_edge(
        self,
        tenant_id: UUID,
        edge_id: UUID,
    ) -> KnowledgeEdge | None:
        with self._connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                SELECT *
                FROM knowledge_graph_edges
                WHERE tenant_id = %s AND id = %s
                """,
                (tenant_id, edge_id),
            )
            row = cursor.fetchone()

        return None if row is None else edge_from_row(row)

    def list_nodes(
        self,
        tenant_id: UUID,
    ) -> tuple[KnowledgeNode, ...]:
        with self._connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                SELECT *
                FROM knowledge_graph_nodes
                WHERE tenant_id = %s
                ORDER BY created_at, id
                """,
                (tenant_id,),
            )
            rows = cursor.fetchall()

        return tuple(node_from_row(row) for row in rows)

    def list_edges(
        self,
        tenant_id: UUID,
    ) -> tuple[KnowledgeEdge, ...]:
        with self._connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                SELECT *
                FROM knowledge_graph_edges
                WHERE tenant_id = %s
                ORDER BY created_at, id
                """,
                (tenant_id,),
            )
            rows = cursor.fetchall()

        return tuple(edge_from_row(row) for row in rows)

    def delete_node(
        self,
        tenant_id: UUID,
        node_id: UUID,
    ) -> None:
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                DELETE FROM knowledge_graph_nodes
                WHERE tenant_id = %s AND id = %s
                """,
                (tenant_id, node_id),
            )
        self._connection.commit()

    def delete_edge(
        self,
        tenant_id: UUID,
        edge_id: UUID,
    ) -> None:
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                DELETE FROM knowledge_graph_edges
                WHERE tenant_id = %s AND id = %s
                """,
                (tenant_id, edge_id),
            )
        self._connection.commit()
