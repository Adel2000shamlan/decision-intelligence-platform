from uuid import uuid4

import pytest

from app.modules.knowledge_graph.persistence.repository import KnowledgeGraphRepository


def test_repository_contract_is_abstract():
    with pytest.raises(TypeError):
        KnowledgeGraphRepository()


def test_repository_contract_defines_required_operations():
    expected = {
        "add_node",
        "add_edge",
        "get_node",
        "get_edge",
        "list_nodes",
        "list_edges",
        "delete_node",
        "delete_edge",
    }

    assert expected.issubset(
        set(KnowledgeGraphRepository.__abstractmethods__)
    )


def test_repository_contract_methods_are_explicitly_abstract():
    tenant_id = uuid4()

    for method_name in (
        "add_node",
        "add_edge",
        "get_node",
        "get_edge",
        "list_nodes",
        "list_edges",
        "delete_node",
        "delete_edge",
    ):
        method = getattr(KnowledgeGraphRepository, method_name)
        assert getattr(method, "__isabstractmethod__", False) is True
