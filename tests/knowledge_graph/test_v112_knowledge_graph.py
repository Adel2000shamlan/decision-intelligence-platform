from uuid import uuid4

import pytest

from app.modules.knowledge_graph import KnowledgeGraphService
from app.modules.knowledge_graph.domain import (
    KnowledgeEdge,
    KnowledgeNode,
    KnowledgeNodeType,
    KnowledgeRelationType,
)
from app.shared.domain.errors import BusinessRuleViolation, InvalidDomainData


def make_node(tenant_id, label, node_type=KnowledgeNodeType.CONCEPT):
    return KnowledgeNode.create(
        tenant_id=tenant_id,
        node_type=node_type,
        label=label,
        source="verified_test_source",
    )


def test_node_creation_requires_valid_core_data():
    tenant_id = uuid4()

    node = make_node(tenant_id, "Revenue")

    assert node.tenant_id == tenant_id
    assert node.label == "Revenue"
    assert node.node_type == KnowledgeNodeType.CONCEPT


def test_node_rejects_invalid_source():
    with pytest.raises(InvalidDomainData, match="source"):
        KnowledgeNode.create(
            uuid4(),
            KnowledgeNodeType.CONCEPT,
            "Revenue",
            " ",
        )


def test_edge_requires_existing_nodes():
    tenant_id = uuid4()
    service = KnowledgeGraphService()

    source = make_node(tenant_id, "Revenue")
    target = make_node(tenant_id, "Project")

    service.add_node(source)

    edge = KnowledgeEdge.create(
        tenant_id,
        source.id,
        target.id,
        KnowledgeRelationType.RELATES_TO,
        "verified_test_source",
    )

    with pytest.raises(
        BusinessRuleViolation,
        match="target node does not exist",
    ):
        service.add_edge(edge)


def test_edge_rejects_self_reference():
    tenant_id = uuid4()
    node = make_node(tenant_id, "Revenue")

    with pytest.raises(
        InvalidDomainData,
        match="self-referencing",
    ):
        KnowledgeEdge.create(
            tenant_id,
            node.id,
            node.id,
            KnowledgeRelationType.RELATES_TO,
            "verified_test_source",
        )


def test_edge_confidence_must_be_between_zero_and_one():
    tenant_id = uuid4()
    node_a = make_node(tenant_id, "Revenue")
    node_b = make_node(tenant_id, "Project")

    with pytest.raises(InvalidDomainData):
        KnowledgeEdge.create(
            tenant_id,
            node_a.id,
            node_b.id,
            KnowledgeRelationType.SUPPORTS,
            "verified_test_source",
            confidence=1.1,
        )

    with pytest.raises(InvalidDomainData):
        KnowledgeEdge.create(
            tenant_id,
            node_a.id,
            node_b.id,
            KnowledgeRelationType.SUPPORTS,
            "verified_test_source",
            confidence=True,
        )


def test_graph_returns_neighbors_for_both_edge_directions():
    tenant_id = uuid4()
    service = KnowledgeGraphService()

    project = make_node(
        tenant_id,
        "Project",
        KnowledgeNodeType.PROJECT,
    )
    risk = make_node(
        tenant_id,
        "Market Risk",
        KnowledgeNodeType.RISK,
    )

    service.add_node(project)
    service.add_node(risk)

    service.add_edge(
        KnowledgeEdge.create(
            tenant_id,
            project.id,
            risk.id,
            KnowledgeRelationType.AFFECTS,
            "verified_test_source",
            confidence=0.9,
        )
    )

    assert service.neighbors(tenant_id, project.id) == (risk,)
    assert service.neighbors(tenant_id, risk.id) == (project,)


def test_graph_is_tenant_isolated():
    tenant_a = uuid4()
    tenant_b = uuid4()
    service = KnowledgeGraphService()

    node_a = make_node(tenant_a, "Tenant A")
    node_b = make_node(tenant_b, "Tenant B")

    service.add_node(node_a)
    service.add_node(node_b)

    target_a = make_node(tenant_a, "A Target")
    service.add_node(target_a)

    service.add_edge(
        KnowledgeEdge.create(
            tenant_a,
            node_a.id,
            target_a.id,
            KnowledgeRelationType.RELATES_TO,
            "verified_test_source",
        )
    )

    assert len(service.nodes(tenant_a)) == 2
    assert len(service.nodes(tenant_b)) == 1
    assert service.neighbors(tenant_b, node_b.id) == ()

def test_edge_cannot_cross_tenant_boundaries():
    tenant_a = uuid4()
    tenant_b = uuid4()
    service = KnowledgeGraphService()

    source_a = make_node(tenant_a, "A Source")
    target_b = make_node(tenant_b, "B Target")

    service.add_node(source_a)
    service.add_node(target_b)

    edge = KnowledgeEdge.create(
        tenant_a,
        source_a.id,
        target_b.id,
        KnowledgeRelationType.RELATES_TO,
        "verified_test_source",
    )

    with pytest.raises(
        BusinessRuleViolation,
        match="target node does not exist",
    ):
        service.add_edge(edge)


def test_edge_cannot_reference_foreign_source_node():
    tenant_a = uuid4()
    tenant_b = uuid4()
    service = KnowledgeGraphService()

    source_b = make_node(tenant_b, "B Source")
    target_a = make_node(tenant_a, "A Target")

    service.add_node(source_b)
    service.add_node(target_a)

    edge = KnowledgeEdge.create(
        tenant_a,
        source_b.id,
        target_a.id,
        KnowledgeRelationType.RELATES_TO,
        "verified_test_source",
    )

    with pytest.raises(
        BusinessRuleViolation,
        match="source node does not exist",
    ):
        service.add_edge(edge)

def test_search_nodes_is_case_insensitive_and_tenant_scoped():
    tenant_a = uuid4()
    tenant_b = uuid4()
    service = KnowledgeGraphService()

    service.add_node(make_node(tenant_a, "Revenue Growth"))
    service.add_node(make_node(tenant_a, "Market Risk"))
    service.add_node(make_node(tenant_b, "Revenue Growth"))

    results = service.search_nodes(tenant_a, "revenue")

    assert len(results) == 1
    assert results[0].label == "Revenue Growth"


def test_search_nodes_requires_query():
    with pytest.raises(InvalidDomainData, match="query"):
        KnowledgeGraphService().search_nodes(uuid4(), " ")


def test_connected_edges_returns_only_edges_for_requested_node():
    tenant_id = uuid4()
    service = KnowledgeGraphService()

    project = make_node(tenant_id, "Project")
    risk = make_node(tenant_id, "Risk")
    kpi = make_node(tenant_id, "KPI")

    service.add_node(project)
    service.add_node(risk)
    service.add_node(kpi)

    edge_one = KnowledgeEdge.create(
        tenant_id,
        project.id,
        risk.id,
        KnowledgeRelationType.AFFECTS,
        "verified_test_source",
    )
    edge_two = KnowledgeEdge.create(
        tenant_id,
        project.id,
        kpi.id,
        KnowledgeRelationType.MEASURES,
        "verified_test_source",
    )

    service.add_edge(edge_one)
    service.add_edge(edge_two)

    connected = service.connected_edges(tenant_id, project.id)

    assert set(connected) == {edge_one, edge_two}

def test_find_path_returns_shortest_available_path_within_depth():
    tenant_id = uuid4()
    service = KnowledgeGraphService()

    project = make_node(tenant_id, "Project")
    risk = make_node(tenant_id, "Risk")
    mitigation = make_node(tenant_id, "Mitigation")
    service.add_node(project)
    service.add_node(risk)
    service.add_node(mitigation)

    service.add_edge(
        KnowledgeEdge.create(
            tenant_id,
            project.id,
            risk.id,
            KnowledgeRelationType.AFFECTS,
            "verified_test_source",
        )
    )
    service.add_edge(
        KnowledgeEdge.create(
            tenant_id,
            risk.id,
            mitigation.id,
            KnowledgeRelationType.MITIGATES,
            "verified_test_source",
        )
    )

    assert service.find_path(
        tenant_id,
        project.id,
        mitigation.id,
        max_depth=2,
    ) == (project.id, risk.id, mitigation.id)


def test_find_path_returns_none_when_depth_is_insufficient():
    tenant_id = uuid4()
    service = KnowledgeGraphService()

    first = make_node(tenant_id, "First")
    second = make_node(tenant_id, "Second")
    third = make_node(tenant_id, "Third")

    service.add_node(first)
    service.add_node(second)
    service.add_node(third)

    service.add_edge(
        KnowledgeEdge.create(
            tenant_id,
            first.id,
            second.id,
            KnowledgeRelationType.RELATES_TO,
            "verified_test_source",
        )
    )
    service.add_edge(
        KnowledgeEdge.create(
            tenant_id,
            second.id,
            third.id,
            KnowledgeRelationType.RELATES_TO,
            "verified_test_source",
        )
    )

    assert service.find_path(
        tenant_id,
        first.id,
        third.id,
        max_depth=1,
    ) is None


def test_find_path_is_tenant_scoped():
    tenant_a = uuid4()
    tenant_b = uuid4()
    service = KnowledgeGraphService()

    start_a = make_node(tenant_a, "A Start")
    target_a = make_node(tenant_a, "A Target")
    start_b = make_node(tenant_b, "B Start")

    service.add_node(start_a)
    service.add_node(target_a)
    service.add_node(start_b)

    service.add_edge(
        KnowledgeEdge.create(
            tenant_a,
            start_a.id,
            target_a.id,
            KnowledgeRelationType.RELATES_TO,
            "verified_test_source",
        )
    )

    with pytest.raises(
        BusinessRuleViolation,
        match="target node does not exist",
    ):
        service.find_path(
            tenant_b,
            start_b.id,
            target_a.id,
        )

def test_node_lookup_is_tenant_scoped():
    tenant_a = uuid4()
    tenant_b = uuid4()
    service = KnowledgeGraphService()

    node = make_node(tenant_a, "Project")
    service.add_node(node)

    assert service.node(tenant_a, node.id) == node
    assert service.node(tenant_b, node.id) is None


def test_edge_lookup_is_tenant_scoped():
    tenant_a = uuid4()
    tenant_b = uuid4()
    service = KnowledgeGraphService()

    source = make_node(tenant_a, "Source")
    target = make_node(tenant_a, "Target")
    service.add_node(source)
    service.add_node(target)

    edge = KnowledgeEdge.create(
        tenant_a,
        source.id,
        target.id,
        KnowledgeRelationType.RELATES_TO,
        "verified_test_source",
    )
    service.add_edge(edge)

    assert service.edge(tenant_a, edge.id) == edge
    assert service.edge(tenant_b, edge.id) is None

def test_remove_node_cascades_connected_edges():
    tenant_id = uuid4()
    service = KnowledgeGraphService()

    project = make_node(tenant_id, "Project")
    risk = make_node(tenant_id, "Risk")

    service.add_node(project)
    service.add_node(risk)

    edge = KnowledgeEdge.create(
        tenant_id,
        project.id,
        risk.id,
        KnowledgeRelationType.AFFECTS,
        "verified_test_source",
    )
    service.add_edge(edge)

    assert service.remove_node(tenant_id, project.id) is True
    assert service.node(tenant_id, project.id) is None
    assert service.edge(tenant_id, edge.id) is None
    assert service.edges(tenant_id) == ()


def test_remove_node_is_tenant_scoped():
    tenant_a = uuid4()
    tenant_b = uuid4()
    service = KnowledgeGraphService()

    node = make_node(tenant_a, "Project")
    service.add_node(node)

    assert service.remove_node(tenant_b, node.id) is False
    assert service.node(tenant_a, node.id) == node


def test_remove_edge_is_tenant_scoped():
    tenant_a = uuid4()
    tenant_b = uuid4()
    service = KnowledgeGraphService()

    source = make_node(tenant_a, "Source")
    target = make_node(tenant_a, "Target")
    service.add_node(source)
    service.add_node(target)

    edge = KnowledgeEdge.create(
        tenant_a,
        source.id,
        target.id,
        KnowledgeRelationType.RELATES_TO,
        "verified_test_source",
    )
    service.add_edge(edge)

    assert service.remove_edge(tenant_b, edge.id) is False
    assert service.edge(tenant_a, edge.id) == edge
    assert service.remove_edge(tenant_a, edge.id) is True
    assert service.edge(tenant_a, edge.id) is None

def test_duplicate_knowledge_node_is_rejected():
    tenant_id = uuid4()
    service = KnowledgeGraphService()

    first = make_node(tenant_id, "Revenue Growth")
    duplicate = KnowledgeNode.create(
        tenant_id,
        first.node_type,
        "revenue growth",
        first.source,
        first.source_uri,
    )

    service.add_node(first)

    with pytest.raises(
        BusinessRuleViolation,
        match="duplicate knowledge node",
    ):
        service.add_node(duplicate)


def test_duplicate_knowledge_edge_is_rejected():
    tenant_id = uuid4()
    service = KnowledgeGraphService()

    source = make_node(tenant_id, "Source")
    target = make_node(tenant_id, "Target")
    service.add_node(source)
    service.add_node(target)

    first = KnowledgeEdge.create(
        tenant_id,
        source.id,
        target.id,
        KnowledgeRelationType.RELATES_TO,
        "verified_test_source",
    )
    duplicate = KnowledgeEdge.create(
        tenant_id,
        source.id,
        target.id,
        KnowledgeRelationType.RELATES_TO,
        "another_verified_source",
    )

    service.add_edge(first)

    with pytest.raises(
        BusinessRuleViolation,
        match="duplicate knowledge edge",
    ):
        service.add_edge(duplicate)


def test_same_edge_between_different_tenants_is_allowed():
    tenant_a = uuid4()
    tenant_b = uuid4()
    service = KnowledgeGraphService()

    source_a = make_node(tenant_a, "Source")
    target_a = make_node(tenant_a, "Target")
    source_b = make_node(tenant_b, "Source")
    target_b = make_node(tenant_b, "Target")

    service.add_node(source_a)
    service.add_node(target_a)
    service.add_node(source_b)
    service.add_node(target_b)

    edge_a = KnowledgeEdge.create(
        tenant_a,
        source_a.id,
        target_a.id,
        KnowledgeRelationType.RELATES_TO,
        "verified_test_source",
    )
    edge_b = KnowledgeEdge.create(
        tenant_b,
        source_b.id,
        target_b.id,
        KnowledgeRelationType.RELATES_TO,
        "verified_test_source",
    )

    assert service.add_edge(edge_a) == edge_a
    assert service.add_edge(edge_b) == edge_b

def test_validate_integrity_passes_for_valid_graph():
    tenant_id = uuid4()
    service = KnowledgeGraphService()

    source = make_node(tenant_id, "Source")
    target = make_node(tenant_id, "Target")
    service.add_node(source)
    service.add_node(target)

    service.add_edge(
        KnowledgeEdge.create(
            tenant_id,
            source.id,
            target.id,
            KnowledgeRelationType.RELATES_TO,
            "verified_test_source",
        )
    )

    assert service.validate_integrity(tenant_id) is True


def test_validate_integrity_rejects_missing_source_node():
    tenant_id = uuid4()
    service = KnowledgeGraphService()

    target = make_node(tenant_id, "Target")
    service.add_node(target)

    edge = KnowledgeEdge.create(
        tenant_id,
        uuid4(),
        target.id,
        KnowledgeRelationType.RELATES_TO,
        "verified_test_source",
    )

    service._edges[tenant_id][edge.id] = edge

    with pytest.raises(
        BusinessRuleViolation,
        match="missing source node",
    ):
        service.validate_integrity(tenant_id)


def test_validate_integrity_rejects_missing_target_node():
    tenant_id = uuid4()
    service = KnowledgeGraphService()

    source = make_node(tenant_id, "Source")
    service.add_node(source)

    edge = KnowledgeEdge.create(
        tenant_id,
        source.id,
        uuid4(),
        KnowledgeRelationType.RELATES_TO,
        "verified_test_source",
    )

    service._edges[tenant_id][edge.id] = edge

    with pytest.raises(
        BusinessRuleViolation,
        match="missing target node",
    ):
        service.validate_integrity(tenant_id)

def test_snapshot_returns_complete_tenant_scoped_graph():
    tenant_a = uuid4()
    tenant_b = uuid4()
    service = KnowledgeGraphService()

    source_a = make_node(tenant_a, "Source A")
    target_a = make_node(tenant_a, "Target A")
    source_b = make_node(tenant_b, "Source B")

    service.add_node(source_a)
    service.add_node(target_a)
    service.add_node(source_b)

    edge_a = KnowledgeEdge.create(
        tenant_a,
        source_a.id,
        target_a.id,
        KnowledgeRelationType.RELATES_TO,
        "verified_test_source",
    )
    service.add_edge(edge_a)

    snapshot = service.snapshot(tenant_a)

    assert set(snapshot.keys()) == {"nodes", "edges"}
    assert set(snapshot["nodes"]) == {source_a, target_a}
    assert set(snapshot["edges"]) == {edge_a}
    assert source_b not in snapshot["nodes"]


def test_snapshot_validates_graph_integrity_before_export():
    tenant_id = uuid4()
    service = KnowledgeGraphService()

    target = make_node(tenant_id, "Target")
    service.add_node(target)

    edge = KnowledgeEdge.create(
        tenant_id,
        uuid4(),
        target.id,
        KnowledgeRelationType.RELATES_TO,
        "verified_test_source",
    )
    service._edges[tenant_id][edge.id] = edge

    with pytest.raises(
        BusinessRuleViolation,
        match="missing source node",
    ):
        service.snapshot(tenant_id)
