from datetime import datetime, timezone
from uuid import uuid4

from app.modules.knowledge_graph.domain.models import (
    KnowledgeEdge,
    KnowledgeNode,
    KnowledgeNodeType,
    KnowledgeRelationType,
)
from app.modules.knowledge_graph.persistence.mappers import (
    edge_from_row,
    edge_to_row,
    node_from_row,
    node_to_row,
)


class Row(dict):
    pass


def test_node_mapper_round_trip():
    node = KnowledgeNode.create(
        tenant_id=uuid4(),
        node_type=KnowledgeNodeType.PROJECT,
        label="Project",
        source="verified_test_source",
        source_uri="https://example.test/project",
    )

    row_values = node_to_row(node)

    row = Row(
        id=row_values[0],
        tenant_id=row_values[1],
        node_type=row_values[2],
        label=row_values[3],
        source=row_values[4],
        source_uri=row_values[5],
        created_at=row_values[6],
    )

    assert node_from_row(row) == node


def test_edge_mapper_round_trip():
    tenant_id = uuid4()

    source = KnowledgeNode.create(
        tenant_id=tenant_id,
        node_type=KnowledgeNodeType.PROJECT,
        label="Source",
        source="verified_test_source",
    )
    target = KnowledgeNode.create(
        tenant_id=tenant_id,
        node_type=KnowledgeNodeType.CONCEPT,
        label="Target",
        source="verified_test_source",
    )

    edge = KnowledgeEdge.create(
        tenant_id=tenant_id,
        source_node_id=source.id,
        target_node_id=target.id,
        relation_type=KnowledgeRelationType.SUPPORTS,
        source="verified_test_source",
        confidence=0.85,
    )

    row_values = edge_to_row(edge)

    row = Row(
        id=row_values[0],
        tenant_id=row_values[1],
        source_node_id=row_values[2],
        target_node_id=row_values[3],
        relation_type=row_values[4],
        source=row_values[5],
        confidence=row_values[6],
        created_at=row_values[7],
    )

    assert edge_from_row(row) == edge


def test_mappers_preserve_timezone_aware_datetime():
    node = KnowledgeNode(
        id=uuid4(),
        tenant_id=uuid4(),
        node_type=KnowledgeNodeType.CONCEPT,
        label="Timezone",
        source="verified_test_source",
        source_uri=None,
        created_at=datetime.now(timezone.utc),
    )

    values = node_to_row(node)

    row = Row(
        id=values[0],
        tenant_id=values[1],
        node_type=values[2],
        label=values[3],
        source=values[4],
        source_uri=values[5],
        created_at=values[6],
    )

    restored = node_from_row(row)

    assert restored.created_at == node.created_at
    assert restored.created_at.tzinfo is not None
