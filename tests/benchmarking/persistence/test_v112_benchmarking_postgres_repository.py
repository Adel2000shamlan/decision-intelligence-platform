import os
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import psycopg
import pytest

from app.modules.benchmarking.domain.models import (
    BenchmarkDataStatus,
    BenchmarkDefinition,
    BenchmarkObservation,
)
from app.modules.benchmarking.persistence.postgres import (
    PostgresBenchmarkingRepository,
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
        repository = PostgresBenchmarkingRepository(connection)

        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM benchmark_observations")
            cursor.execute("DELETE FROM benchmark_definitions")
            connection.commit()

        yield repository

        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM benchmark_observations")
            cursor.execute("DELETE FROM benchmark_definitions")
            connection.commit()


def make_definition(tenant_id):
    return BenchmarkDefinition.create(
        tenant_id=tenant_id,
        metric="monthly_revenue",
        unit="EGP",
        methodology="peer_group_mean",
        source="verified_test_source",
        minimum_observations=2,
    )


def make_observation(
    tenant_id,
    definition_id,
    *,
    peer_group="cairo_cafes",
    value=1000.0,
    evidence_id=None,
):
    return BenchmarkObservation.create(
        tenant_id=tenant_id,
        definition_id=definition_id,
        peer_group=peer_group,
        metric="monthly_revenue",
        unit="EGP",
        value=value,
        status=BenchmarkDataStatus.OBSERVED,
        evidence="verified_test_evidence",
        evidence_id=evidence_id or uuid4(),
        observed_at=datetime.now(timezone.utc) - timedelta(minutes=1),
    )


def test_definition_crud(repository):
    tenant_id = uuid4()
    definition = make_definition(tenant_id)

    assert repository.save_definition(definition) == definition
    assert repository.get_definition(tenant_id, definition.id) == definition
    assert repository.list_definitions(tenant_id) == (definition,)

    repository.delete_definition(tenant_id, definition.id)

    assert repository.get_definition(tenant_id, definition.id) is None
    assert repository.list_definitions(tenant_id) == ()


def test_observation_crud(repository):
    tenant_id = uuid4()
    definition = make_definition(tenant_id)
    repository.save_definition(definition)

    observation = make_observation(
        tenant_id,
        definition.id,
        value=1250.0,
    )

    assert repository.save_observation(observation) == observation
    assert repository.get_observation(
        tenant_id,
        observation.id,
    ) == observation
    assert repository.list_observations(tenant_id) == (observation,)

    repository.delete_observation(tenant_id, observation.id)

    assert repository.get_observation(
        tenant_id,
        observation.id,
    ) is None
    assert repository.list_observations(tenant_id) == ()


def test_tenant_isolation(repository):
    tenant_a = uuid4()
    tenant_b = uuid4()

    definition_a = make_definition(tenant_a)
    definition_b = make_definition(tenant_b)

    repository.save_definition(definition_a)
    repository.save_definition(definition_b)

    assert repository.get_definition(
        tenant_a,
        definition_b.id,
    ) is None
    assert repository.get_definition(
        tenant_b,
        definition_a.id,
    ) is None

    assert repository.list_definitions(tenant_a) == (definition_a,)
    assert repository.list_definitions(tenant_b) == (definition_b,)


def test_observation_filters(repository):
    tenant_id = uuid4()
    definition = make_definition(tenant_id)
    repository.save_definition(definition)

    first = make_observation(
        tenant_id,
        definition.id,
        peer_group="group_a",
        value=1000.0,
    )
    second = make_observation(
        tenant_id,
        definition.id,
        peer_group="group_b",
        value=2000.0,
    )

    repository.save_observation(first)
    repository.save_observation(second)

    assert repository.list_observations(
        tenant_id,
        definition_id=definition.id,
    ) == (first, second)

    assert repository.list_observations(
        tenant_id,
        peer_group="group_a",
    ) == (first,)

    assert repository.list_observations(
        tenant_id,
        metric="monthly_revenue",
    ) == (first, second)


def test_duplicate_definition_is_rejected(repository):
    tenant_id = uuid4()
    definition = make_definition(tenant_id)

    repository.save_definition(definition)

    with pytest.raises(
        BusinessRuleViolation,
        match="duplicate benchmark definition",
    ):
        repository.save_definition(definition)


def test_duplicate_observation_is_rejected(repository):
    tenant_id = uuid4()
    definition = make_definition(tenant_id)
    repository.save_definition(definition)

    observation = make_observation(
        tenant_id,
        definition.id,
    )
    repository.save_observation(observation)

    with pytest.raises(
        BusinessRuleViolation,
        match="duplicate benchmark observation",
    ):
        repository.save_observation(observation)


def test_observation_requires_existing_definition(repository):
    tenant_id = uuid4()

    observation = make_observation(
        tenant_id,
        uuid4(),
    )

    with pytest.raises(
        BusinessRuleViolation,
        match="benchmark definition does not exist",
    ):
        repository.save_observation(observation)


def test_deleting_definition_cascades_observations(repository):
    tenant_id = uuid4()
    definition = make_definition(tenant_id)
    repository.save_definition(definition)

    observation = make_observation(
        tenant_id,
        definition.id,
    )
    repository.save_observation(observation)

    repository.delete_definition(tenant_id, definition.id)

    assert repository.get_definition(
        tenant_id,
        definition.id,
    ) is None
    assert repository.get_observation(
        tenant_id,
        observation.id,
    ) is None
    assert repository.list_observations(tenant_id) == ()


def test_evidence_id_roundtrip(repository):
    tenant_id = uuid4()
    definition = make_definition(tenant_id)
    repository.save_definition(definition)

    evidence_id = uuid4()
    observation = make_observation(
        tenant_id,
        definition.id,
        evidence_id=evidence_id,
    )

    repository.save_observation(observation)

    restored = repository.get_observation(
        tenant_id,
        observation.id,
    )

    assert restored is not None
    assert restored.evidence_id == evidence_id


def test_database_rejects_cross_tenant_definition_reference(repository):
    tenant_a = uuid4()
    tenant_b = uuid4()

    definition_a = make_definition(tenant_a)
    repository.save_definition(definition_a)

    observation_id = uuid4()
    evidence_id = uuid4()
    observed_at = datetime.now(timezone.utc) - timedelta(minutes=1)

    with pytest.raises(psycopg.IntegrityError):
        with repository._connection.cursor() as cursor:
            cursor.execute(
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
                VALUES (
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s
                )
                """,
                (
                    observation_id,
                    tenant_b,
                    definition_a.id,
                    "cross_tenant",
                    "monthly_revenue",
                    "EGP",
                    1000.0,
                    "observed",
                    "direct database test",
                    evidence_id,
                    observed_at,
                ),
            )

    repository._connection.rollback()
