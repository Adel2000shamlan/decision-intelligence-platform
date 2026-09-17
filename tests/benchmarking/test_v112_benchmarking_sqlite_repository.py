import sqlite3
from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.modules.benchmarking.domain.models import (
    BenchmarkDataStatus,
    BenchmarkDefinition,
    BenchmarkObservation,
)
from app.modules.benchmarking.persistence.sqlite import (
    SQLiteBenchmarkingRepository,
)
from app.shared.domain.errors import BusinessRuleViolation


def make_definition(tenant_id):
    return BenchmarkDefinition.create(
        tenant_id=tenant_id,
        metric="monthly_revenue",
        unit="EGP",
        methodology="peer_mean",
        source="verified_test_source",
        minimum_observations=2,
    )


def make_observation(tenant_id, definition_id, *, value=100000, peer_group="cairo_cafes"):
    return BenchmarkObservation.create(
        tenant_id=tenant_id,
        definition_id=definition_id,
        peer_group=peer_group,
        metric="monthly_revenue",
        unit="EGP",
        value=value,
        status=BenchmarkDataStatus.OBSERVED,
        evidence="verified source",
        evidence_id=uuid4(),
        observed_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def repository():
    connection = sqlite3.connect(":memory:")
    repository = SQLiteBenchmarkingRepository(connection)
    yield repository
    connection.close()


def test_definition_crud_roundtrip(repository):
    tenant_id = uuid4()
    definition = make_definition(tenant_id)

    assert repository.save_definition(definition) == definition
    assert repository.get_definition(tenant_id, definition.id) == definition
    assert repository.list_definitions(tenant_id) == (definition,)

    repository.delete_definition(tenant_id, definition.id)

    assert repository.get_definition(tenant_id, definition.id) is None
    assert repository.list_definitions(tenant_id) == ()


def test_observation_crud_roundtrip(repository):
    tenant_id = uuid4()
    definition = make_definition(tenant_id)
    repository.save_definition(definition)

    observation = make_observation(tenant_id, definition.id)

    assert repository.save_observation(observation) == observation
    assert repository.get_observation(tenant_id, observation.id) == observation
    assert repository.list_observations(tenant_id) == (observation,)

    repository.delete_observation(tenant_id, observation.id)

    assert repository.get_observation(tenant_id, observation.id) is None
    assert repository.list_observations(tenant_id) == ()


def test_tenant_isolation(repository):
    tenant_a = uuid4()
    tenant_b = uuid4()

    definition = make_definition(tenant_a)
    repository.save_definition(definition)

    observation = make_observation(tenant_a, definition.id)
    repository.save_observation(observation)

    assert repository.get_definition(tenant_b, definition.id) is None
    assert repository.get_observation(tenant_b, observation.id) is None
    assert repository.list_definitions(tenant_b) == ()
    assert repository.list_observations(tenant_b) == ()

    repository.delete_definition(tenant_b, definition.id)

    assert repository.get_definition(tenant_a, definition.id) == definition
    assert repository.get_observation(tenant_a, observation.id) == observation


def test_observation_filters(repository):
    tenant_id = uuid4()
    definition = make_definition(tenant_id)
    repository.save_definition(definition)

    first = make_observation(
        tenant_id,
        definition.id,
        value=100000,
        peer_group="cairo_cafes",
    )
    second = make_observation(
        tenant_id,
        definition.id,
        value=150000,
        peer_group="giza_cafes",
    )

    repository.save_observation(first)
    repository.save_observation(second)

    assert repository.list_observations(
        tenant_id,
        definition_id=definition.id,
    ) == (first, second)

    assert repository.list_observations(
        tenant_id,
        peer_group="cairo_cafes",
    ) == (first,)

    assert repository.list_observations(
        tenant_id,
        metric="monthly_revenue",
    ) == (first, second)


def test_duplicate_definition_id_rejected(repository):
    tenant_id = uuid4()
    definition = make_definition(tenant_id)

    repository.save_definition(definition)

    duplicate = BenchmarkDefinition(
        id=definition.id,
        tenant_id=tenant_id,
        metric="different_metric",
        unit="EGP",
        methodology="peer_mean",
        source="source",
        minimum_observations=2,
    )

    with pytest.raises(BusinessRuleViolation, match="duplicate benchmark definition"):
        repository.save_definition(duplicate)


def test_duplicate_observation_id_rejected(repository):
    tenant_id = uuid4()
    definition = make_definition(tenant_id)
    repository.save_definition(definition)

    observation = make_observation(tenant_id, definition.id)
    repository.save_observation(observation)

    duplicate = BenchmarkObservation(
        id=observation.id,
        tenant_id=tenant_id,
        definition_id=definition.id,
        peer_group="cairo_cafes",
        metric="monthly_revenue",
        unit="EGP",
        value=200000,
        status=BenchmarkDataStatus.OBSERVED,
        evidence="another source",
        evidence_id=uuid4(),
        observed_at=datetime.now(timezone.utc),
    )

    with pytest.raises(BusinessRuleViolation, match="duplicate benchmark observation"):
        repository.save_observation(duplicate)


def test_observation_requires_existing_definition(repository):
    tenant_id = uuid4()
    missing_definition_id = uuid4()

    observation = make_observation(tenant_id, missing_definition_id)

    with pytest.raises(
        BusinessRuleViolation,
        match="benchmark definition does not exist",
    ):
        repository.save_observation(observation)


def test_delete_definition_cascades_observations(repository):
    tenant_id = uuid4()
    definition = make_definition(tenant_id)
    repository.save_definition(definition)

    observation = make_observation(tenant_id, definition.id)
    repository.save_observation(observation)

    repository.delete_definition(tenant_id, definition.id)

    assert repository.get_definition(tenant_id, definition.id) is None
    assert repository.get_observation(tenant_id, observation.id) is None
    assert repository.list_observations(tenant_id) == ()


def test_evidence_id_roundtrip(repository):
    tenant_id = uuid4()
    definition = make_definition(tenant_id)
    repository.save_definition(definition)

    evidence_id = uuid4()
    observation = BenchmarkObservation.create(
        tenant_id=tenant_id,
        definition_id=definition.id,
        peer_group="cairo_cafes",
        metric="monthly_revenue",
        unit="EGP",
        value=123456.75,
        status=BenchmarkDataStatus.DERIVED,
        evidence="derived from verified observations",
        evidence_id=evidence_id,
        observed_at=datetime.now(timezone.utc),
    )

    repository.save_observation(observation)
    loaded = repository.get_observation(tenant_id, observation.id)

    assert loaded is not None
    assert loaded.evidence_id == evidence_id
    assert loaded.status is BenchmarkDataStatus.DERIVED
    assert loaded.value == 123456.75

def test_database_rejects_cross_tenant_definition_reference(repository):
    tenant_a = uuid4()
    tenant_b = uuid4()

    definition = make_definition(tenant_a)
    repository.save_definition(definition)

    observation = make_observation(
        tenant_b,
        definition.id,
    )

    with pytest.raises(sqlite3.IntegrityError):
        repository._connection.execute(
            """
            INSERT INTO benchmark_observations
            (
                id,
                tenant_id,
                definition_id,
                peer_group,
                metric,
                unit,
                value,
                status,
                evidence,
                evidence_id,
                observed_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(observation.id),
                str(observation.tenant_id),
                str(observation.definition_id),
                observation.peer_group,
                observation.metric,
                observation.unit,
                observation.value,
                observation.status.value,
                observation.evidence,
                str(observation.evidence_id),
                observation.observed_at.isoformat(),
            ),
        )
