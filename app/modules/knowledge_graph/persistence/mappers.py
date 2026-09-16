from datetime import datetime
from uuid import UUID

from ..domain.models import KnowledgeEdge, KnowledgeNode


def node_to_row(node: KnowledgeNode) -> tuple:
    return (
        str(node.id),
        str(node.tenant_id),
        node.node_type.value,
        node.label,
        node.source,
        node.source_uri,
        node.created_at.isoformat(),
    )


def edge_to_row(edge: KnowledgeEdge) -> tuple:
    return (
        str(edge.id),
        str(edge.tenant_id),
        str(edge.source_node_id),
        str(edge.target_node_id),
        edge.relation_type.value,
        edge.source,
        edge.confidence,
        edge.created_at.isoformat(),
    )


def node_from_row(row) -> KnowledgeNode:
    return KnowledgeNode(
        id=UUID(str(row["id"])),
        tenant_id=UUID(str(row["tenant_id"])),
        node_type=row["node_type"],
        label=row["label"],
        source=row["source"],
        source_uri=row["source_uri"],
        created_at=(
            row["created_at"]
            if isinstance(row["created_at"], datetime)
            else datetime.fromisoformat(str(row["created_at"]))
        ),
    )


def edge_from_row(row) -> KnowledgeEdge:
    return KnowledgeEdge(
        id=UUID(str(row["id"])),
        tenant_id=UUID(str(row["tenant_id"])),
        source_node_id=UUID(str(row["source_node_id"])),
        target_node_id=UUID(str(row["target_node_id"])),
        relation_type=row["relation_type"],
        source=row["source"],
        confidence=row["confidence"],
        created_at=(
            row["created_at"]
            if isinstance(row["created_at"], datetime)
            else datetime.fromisoformat(str(row["created_at"]))
        ),
    )
