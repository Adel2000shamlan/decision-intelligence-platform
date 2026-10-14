from abc import ABC, abstractmethod
from uuid import UUID

from ..domain.models import KnowledgeEdge, KnowledgeNode


class KnowledgeGraphRepository(ABC):
    @abstractmethod
    def add_node(self, node: KnowledgeNode) -> KnowledgeNode:
        raise NotImplementedError

    @abstractmethod
    def add_edge(self, edge: KnowledgeEdge) -> KnowledgeEdge:
        raise NotImplementedError

    @abstractmethod
    def get_node(self, tenant_id: UUID, node_id: UUID) -> KnowledgeNode | None:
        raise NotImplementedError

    @abstractmethod
    def get_edge(self, tenant_id: UUID, edge_id: UUID) -> KnowledgeEdge | None:
        raise NotImplementedError

    @abstractmethod
    def list_nodes(self, tenant_id: UUID) -> tuple[KnowledgeNode, ...]:
        raise NotImplementedError

    @abstractmethod
    def list_edges(self, tenant_id: UUID) -> tuple[KnowledgeEdge, ...]:
        raise NotImplementedError

    @abstractmethod
    def delete_node(self, tenant_id: UUID, node_id: UUID) -> None:
        raise NotImplementedError

    @abstractmethod
    def delete_edge(self, tenant_id: UUID, edge_id: UUID) -> None:
        raise NotImplementedError
