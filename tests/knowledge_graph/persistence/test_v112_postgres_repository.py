import os
from uuid import uuid4

import psycopg
import pytest

from app.modules.knowledge_graph.domain.models import (
    KnowledgeEdge,
    KnowledgeNode,
    KnowledgeNodeType,
    KnowledgeRelationType,
)
from app.modules.knowledge_graph.persistence.postgres import (
    PostgresKnowledgeGraphRepository,
)
from app.shared.domain.errors import BusinessRuleViolation


DATABASE_URL = os.getenv("DATABASE_URL")


pytestmark = pytest.mark.skipif(
    not DATABASE_URL,
    reason="DATABASE_URL is not configured",
)


@pytest.fixture
def repository():
    with psycopg.connect(DATABASE_URL) as connection:
        repository = PostgresKnowledgeGraphRepository(connection)

        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM knowledge_graph_edges")
            cursor.execute("DELETE FROM knowledge_graph_nodes")
        connection.commit()

        yield repository

        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM knowledge_graph_edges")
            cursor.execute("DELETE FROM knowledge_graph_nodes")
        connection.commit()


def make_node(tenant_id, label="Node"):
    return KnowledgeNode.create(
        tenant_id=tenant_id,
        node_type=KnowledgeNodeType.CONCEPT,
        label=label,
        source="verified_test_source",
    )


def make_edge(tenant_id, source_id, target_id):
    return KnowledgeEdge.create(
        tenant_id=tenant_id,
        source_node_id=source_id,
        target_node_id=target_id,
        relation_type=KnowledgeRelationType.RELATES_TO,
        source="verified_test_source",
        confidence=0.9,
    )


def test_node_crud(repository):
    tenant_id = uuid4()
    node = make_node(tenant_id, "Postgres Node")

    assert repository.add_node(node) == node
    assert repository.get_node(tenant_id, node.id) == node
    assert repository.list_nodes(tenant_id) == (node,)

    repository.delete_node(tenant_id, node.id)

    assert repository.get_node(tenant_id, node.id) is None
    assert repository.list_nodes(tenant_id) == ()


def test_edge_crud(repository):
    tenant_id = uuid4()
    source = make_node(tenant_id, "Source")
    target = make_node(tenant_id, "Target")

    repository.add_node(source)
    repository.add_node(target)

    edge = make_edge(tenant_id, source.id, target.id)

    assert repository.add_edge(edge) == edge
    assert repository.get_edge(tenant_id, edge.id) == edge
    assert repository.list_edges(tenant_id) == (edge,)

    repository.delete_edge(tenant_id, edge.id)

    assert repository.get_edge(tenant_id, edge.id) is None
    assert repository.list_edges(tenant_id) == ()


def test_tenant_isolation(repository):
    tenant_a = uuid4()
    tenant_b = uuid4()

    node_a = make_node(tenant_a, "Tenant A")
    node_b = make_node(tenant_b, "Tenant B")

    repository.add_node(node_a)
    repository.add_node(node_b)

    assert repository.get_node(tenant_a, node_b.id) is None
    assert repository.get_node(tenant_b, node_a.id) is None
    assert repository.list_nodes(tenant_a) == (node_a,)
    assert repository.list_nodes(tenant_b) == (node_b,)


def test_duplicate_node_is_rejected(repository):
    tenant_id = uuid4()

    node = make_node(tenant_id, "Duplicate")
    repository.add_node(node)

    duplicate = KnowledgeNode(
        id=uuid4(),
        tenant_id=node.tenant_id,
        node_type=node.node_type,
        label=node.label,
        source=node.source,
        source_uri=node.source_uri,
        created_at=node.created_at,
    )

    with pytest.raises(
        BusinessRuleViolation,
        match="duplicate knowledge node",
    ):
        repository.add_node(duplicate)


def test_edge_requires_existing_nodes(repository):
    tenant_id = uuid4()
    source = make_node(tenant_id, "Source")
    target = make_node(tenant_id, "Target")

    edge = make_edge(tenant_id, source.id, target.id)

    with pytest.raises(
        BusinessRuleViolation,
        match="source node does not exist",
    ):
        repository.add_edge(edge)


def test_duplicate_edge_is_rejected(repository):
    tenant_id = uuid4()
    source = make_node(tenant_id, "Source")
    target = make_node(tenant_id, "Target")

    repository.add_node(source)
    repository.add_node(target)

    edge = make_edge(tenant_id, source.id, target.id)
    repository.add_edge(edge)

    duplicate = KnowledgeEdge(
        id=uuid4(),
        tenant_id=edge.tenant_id,
        source_node_id=edge.source_node_id,
        target_node_id=edge.target_node_id,
        relation_type=edge.relation_type,
        source=edge.source,
        confidence=edge.confidence,
        created_at=edge.created_at,
    )

    with pytest.raises(
        BusinessRuleViolation,
        match="duplicate knowledge edge",
    ):
        repository.add_edge(duplicate)


def test_edge_cannot_cross_tenant_boundaries(repository):
    tenant_a = uuid4()
    tenant_b = uuid4()

    source_a = make_node(tenant_a, "Source A")
    target_b = make_node(tenant_b, "Target B")

    repository.add_node(source_a)
    repository.add_node(target_b)

    edge = make_edge(
        tenant_a,
        source_a.id,
        target_b.id,
    )

    with pytest.raises(
        BusinessRuleViolation,
        match="target node does not exist",
    ):
        repository.add_edge(edge)


def test_edge_is_invisible_to_other_tenants(repository):
    tenant_a = uuid4()
    tenant_b = uuid4()

    source = make_node(tenant_a, "Source")
    target = make_node(tenant_a, "Target")

    repository.add_node(source)
    repository.add_node(target)

    edge = make_edge(tenant_a, source.id, target.id)
    repository.add_edge(edge)

    assert repository.get_edge(tenant_a, edge.id) == edge
    assert repository.get_edge(tenant_b, edge.id) is None
    assert repository.list_edges(tenant_b) == ()


def test_deleting_node_cascades_edges(repository):
    tenant_id = uuid4()

    source = make_node(tenant_id, "Source")
    target = make_node(tenant_id, "Target")

    repository.add_node(source)
    repository.add_node(target)

    edge = make_edge(tenant_id, source.id, target.id)
    repository.add_edge(edge)

    repository.delete_node(tenant_id, source.id)

    assert repository.get_node(tenant_id, source.id) is None
    assert repository.get_edge(tenant_id, edge.id) is None
    assert repository.list_edges(tenant_id) == ()
