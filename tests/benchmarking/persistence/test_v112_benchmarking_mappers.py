from datetime import datetime, timezone
from uuid import uuid4

from app.modules.benchmarking.domain.models import (
    BenchmarkDataStatus,
    BenchmarkDefinition,
    BenchmarkObservation,
)
from app.modules.benchmarking.persistence.mappers import (
    definition_from_row,
    definition_to_row,
    observation_from_row,
    observation_to_row,
)


def make_definition():
    return BenchmarkDefinition.create(
        tenant_id=uuid4(),
        metric="monthly_revenue",
        unit="EGP",
        methodology="peer_group_mean",
        source="verified_test_source",
        minimum_observations=3,
    )


def make_observation(definition):
    return BenchmarkObservation.create(
        tenant_id=definition.tenant_id,
        definition_id=definition.id,
        peer_group="cairo_cafes",
        metric=definition.metric,
        unit=definition.unit,
        value=1250.5,
        status=BenchmarkDataStatus.OBSERVED,
        evidence="verified_test_evidence",
        evidence_id=uuid4(),
        observed_at=datetime.now(timezone.utc),
    )


def test_definition_mapper_roundtrip():
    definition = make_definition()

    row = {
        "id": definition.id,
        "tenant_id": definition.tenant_id,
        "metric": definition.metric,
        "unit": definition.unit,
        "methodology": definition.methodology,
        "source": definition.source,
        "minimum_observations": definition.minimum_observations,
    }

    assert definition_from_row(row) == definition
    assert definition_to_row(definition) == (
        definition.id,
        definition.tenant_id,
        definition.metric,
        definition.unit,
        definition.methodology,
        definition.source,
        definition.minimum_observations,
    )


def test_observation_mapper_roundtrip():
    definition = make_definition()
    observation = make_observation(definition)

    row = {
        "id": observation.id,
        "tenant_id": observation.tenant_id,
        "definition_id": observation.definition_id,
        "peer_group": observation.peer_group,
        "metric": observation.metric,
        "unit": observation.unit,
        "value": observation.value,
        "status": observation.status.value,
        "evidence": observation.evidence,
        "evidence_id": observation.evidence_id,
        "observed_at": observation.observed_at,
    }

    assert observation_from_row(row) == observation
    assert observation_to_row(observation) == (
        observation.id,
        observation.tenant_id,
        observation.definition_id,
        observation.peer_group,
        observation.metric,
        observation.unit,
        observation.value,
        observation.status.value,
        observation.evidence,
        observation.evidence_id,
        observation.observed_at,
    )


def test_observation_mapper_supports_iso_timestamp():
    definition = make_definition()
    observation = make_observation(definition)

    row = {
        "id": str(observation.id),
        "tenant_id": str(observation.tenant_id),
        "definition_id": str(observation.definition_id),
        "peer_group": observation.peer_group,
        "metric": observation.metric,
        "unit": observation.unit,
        "value": observation.value,
        "status": observation.status.value,
        "evidence": observation.evidence,
        "evidence_id": str(observation.evidence_id),
        "observed_at": observation.observed_at.isoformat(),
    }

    restored = observation_from_row(row)

    assert restored == observation
