from uuid import UUID

import pytest

from app.modules.benchmarking.persistence.repository import (
    BenchmarkingRepository,
)


def test_repository_is_abstract():
    with pytest.raises(TypeError):
        BenchmarkingRepository()


def test_repository_declares_definition_operations():
    assert hasattr(BenchmarkingRepository, "save_definition")
    assert hasattr(BenchmarkingRepository, "get_definition")
    assert hasattr(BenchmarkingRepository, "list_definitions")
    assert hasattr(BenchmarkingRepository, "delete_definition")


def test_repository_declares_observation_operations():
    assert hasattr(BenchmarkingRepository, "save_observation")
    assert hasattr(BenchmarkingRepository, "get_observation")
    assert hasattr(BenchmarkingRepository, "list_observations")
    assert hasattr(BenchmarkingRepository, "delete_observation")


def test_repository_methods_are_abstract():
    abstract_methods = BenchmarkingRepository.__abstractmethods__

    expected = {
        "save_definition",
        "get_definition",
        "list_definitions",
        "delete_definition",
        "save_observation",
        "get_observation",
        "list_observations",
        "delete_observation",
    }

    assert abstract_methods == expected


def test_repository_contract_uses_uuid_annotations():
    annotations = BenchmarkingRepository.get_definition.__annotations__

    assert annotations["tenant_id"] is UUID
    assert annotations["definition_id"] is UUID
