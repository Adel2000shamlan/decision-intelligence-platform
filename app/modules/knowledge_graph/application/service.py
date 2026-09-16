from collections import defaultdict
from uuid import UUID
import sqlite3

from app.shared.domain.errors import BusinessRuleViolation, InvalidDomainData

from ..domain.models import KnowledgeEdge, KnowledgeNode
from ..persistence.repository import KnowledgeGraphRepository
from ..persistence.sqlite import SQLiteKnowledgeGraphRepository


class KnowledgeGraphService:
    def __init__(self, repository: KnowledgeGraphRepository | None = None):
        self._compatibility_edges: dict[UUID, dict[UUID, KnowledgeEdge]] = defaultdict(dict)

        if repository is None:
            connection = sqlite3.connect(":memory:")
            self._repository = SQLiteKnowledgeGraphRepository(connection)
        else:
            self._repository = repository

        # Backward-compatible test surface. Repository remains the source of truth.
        self._edges = self._compatibility_edges

    def add_node(self, node: KnowledgeNode) -> KnowledgeNode:
        existing = self._repository.list_nodes(node.tenant_id)
        node_key = (
            node.node_type,
            node.label.casefold(),
            node.source,
            node.source_uri or "",
        )
        for item in existing:
            item_key = (
                item.node_type,
                item.label.casefold(),
                item.source,
                item.source_uri or "",
            )
            if item_key == node_key:
                raise BusinessRuleViolation("duplicate knowledge node")
        return self._repository.add_node(node)

    def add_edge(self, edge: KnowledgeEdge) -> KnowledgeEdge:
        source = self._repository.get_node(edge.tenant_id, edge.source_node_id)
        if source is None:
            raise BusinessRuleViolation("source node does not exist")

        target = self._repository.get_node(edge.tenant_id, edge.target_node_id)
        if target is None:
            raise BusinessRuleViolation("target node does not exist")

        return self._repository.add_edge(edge)

    def node(self, tenant_id: UUID, node_id: UUID) -> KnowledgeNode | None:
        return self._repository.get_node(tenant_id, node_id)

    def nodes(self, tenant_id: UUID) -> tuple[KnowledgeNode, ...]:
        return self._repository.list_nodes(tenant_id)

    def edge(self, tenant_id: UUID, edge_id: UUID) -> KnowledgeEdge | None:
        repository_edge = self._repository.get_edge(tenant_id, edge_id)
        if repository_edge is not None:
            if (
                self.node(tenant_id, repository_edge.source_node_id) is None
                or self.node(tenant_id, repository_edge.target_node_id) is None
            ):
                return None
            return repository_edge

        compatibility_edge = self._edges.get(tenant_id, {}).get(edge_id)
        return compatibility_edge

    def edges(self, tenant_id: UUID) -> tuple[KnowledgeEdge, ...]:
        repository_edges = {}
        for edge in self._repository.list_edges(tenant_id):
            if (
                self.node(tenant_id, edge.source_node_id) is not None
                and self.node(tenant_id, edge.target_node_id) is not None
            ):
                repository_edges[edge.id] = edge

        repository_edges.update(self._edges.get(tenant_id, {}))
        return tuple(repository_edges.values())

    def search_nodes(
        self,
        tenant_id: UUID,
        query: str,
    ) -> tuple[KnowledgeNode, ...]:
        if not isinstance(query, str) or not query.strip():
            raise InvalidDomainData("query is required")

        needle = query.strip().casefold()
        return tuple(
            node
            for node in self.nodes(tenant_id)
            if needle in node.label.casefold()
        )

    def connected_edges(
        self,
        tenant_id: UUID,
        node_id: UUID,
    ) -> tuple[KnowledgeEdge, ...]:
        return tuple(
            edge
            for edge in self.edges(tenant_id)
            if edge.source_node_id == node_id
            or edge.target_node_id == node_id
        )

    def neighbors(
        self,
        tenant_id: UUID,
        node_id: UUID,
    ) -> tuple[KnowledgeNode, ...]:
        node = self.node(tenant_id, node_id)
        if node is None:
            return ()

        neighbor_ids: set[UUID] = set()
        for edge in self.connected_edges(tenant_id, node_id):
            if edge.source_node_id == node_id:
                neighbor_ids.add(edge.target_node_id)
            else:
                neighbor_ids.add(edge.source_node_id)

        return tuple(
            neighbor
            for neighbor in self.nodes(tenant_id)
            if neighbor.id in neighbor_ids
        )

    def find_path(
        self,
        tenant_id: UUID,
        start_node_id: UUID,
        target_node_id: UUID,
        max_depth: int = 5,
    ) -> tuple[UUID, ...] | None:
        if max_depth < 1:
            raise InvalidDomainData("max_depth must be >= 1")

        start_node = self.node(tenant_id, start_node_id)
        if start_node is None:
            return None

        target_node = self.node(tenant_id, target_node_id)
        if target_node is None:
            raise BusinessRuleViolation("target node does not exist")

        if start_node_id == target_node_id:
            return (start_node_id,)

        adjacency: dict[UUID, set[UUID]] = defaultdict(set)

        for edge in self.edges(tenant_id):
            adjacency[edge.source_node_id].add(edge.target_node_id)
            adjacency[edge.target_node_id].add(edge.source_node_id)

        queue: list[tuple[UUID, tuple[UUID, ...]]] = [
            (start_node_id, (start_node_id,))
        ]
        visited = {start_node_id}

        while queue:
            current, path = queue.pop(0)

            if len(path) - 1 >= max_depth:
                continue

            for neighbor in adjacency.get(current, set()):
                if neighbor in visited:
                    continue

                next_path = path + (neighbor,)

                if neighbor == target_node_id:
                    return next_path

                visited.add(neighbor)
                queue.append((neighbor, next_path))

        return None

    def remove_node(self, tenant_id: UUID, node_id: UUID) -> bool:
        if self.node(tenant_id, node_id) is None:
            return False

        self._repository.delete_node(tenant_id, node_id)
        self._edges.pop(tenant_id, None)
        return True

    def remove_edge(self, tenant_id: UUID, edge_id: UUID) -> bool:
        existing = self.edge(tenant_id, edge_id)
        if existing is None:
            return False

        self._repository.delete_edge(tenant_id, edge_id)
        self._edges.get(tenant_id, {}).pop(edge_id, None)
        return True

    def validate_integrity(self, tenant_id: UUID) -> bool:
        nodes = self.nodes(tenant_id)
        node_ids = {node.id for node in nodes}

        for edge in self.edges(tenant_id):
            if edge.source_node_id not in node_ids:
                raise BusinessRuleViolation(
                    "knowledge graph contains missing source node"
                )

            if edge.target_node_id not in node_ids:
                raise BusinessRuleViolation(
                    "knowledge graph contains missing target node"
                )

        return True

    def snapshot(self, tenant_id: UUID) -> dict[str, tuple]:
        self.validate_integrity(tenant_id)
        return {
            "nodes": self.nodes(tenant_id),
            "edges": self.edges(tenant_id),
        }
