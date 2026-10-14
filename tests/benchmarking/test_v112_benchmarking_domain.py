from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from app.shared.domain.errors import BusinessRuleViolation
from app.modules.benchmarking.domain.models import (
    BenchmarkDataStatus,
    BenchmarkDefinition,
    BenchmarkObservation,
)


def test_definition_requires_valid_minimum_observations():
    with pytest.raises(BusinessRuleViolation):
        BenchmarkDefinition.create(
            tenant_id=uuid4(),
            metric="revenue",
            unit="EGP",
            methodology="peer mean",
            source="internal",
            minimum_observations=1,
        )


def test_definition_creation_is_normalized():
    tenant_id = uuid4()

    definition = BenchmarkDefinition.create(
        tenant_id=tenant_id,
        metric=" revenue ",
        unit=" EGP ",
        methodology=" peer mean ",
        source=" internal ",
    )

    assert definition.tenant_id == tenant_id
    assert definition.metric == "revenue"
    assert definition.unit == "EGP"
    assert definition.methodology == "peer mean"
    assert definition.source == "internal"
    assert definition.minimum_observations == 3


def test_observation_rejects_future_timestamp():
    with pytest.raises(BusinessRuleViolation):
        BenchmarkObservation.create(
            tenant_id=uuid4(),
            definition_id=uuid4(),
            peer_group="faisal-cafes",
            metric="revenue",
            unit="EGP",
            value=1000,
            status=BenchmarkDataStatus.OBSERVED,
            evidence="source-1",
            observed_at=datetime.now(timezone.utc) + timedelta(minutes=1),
        )


def test_observation_rejects_non_finite_value():
    with pytest.raises(BusinessRuleViolation):
        BenchmarkObservation.create(
            tenant_id=uuid4(),
            definition_id=uuid4(),
            peer_group="faisal-cafes",
            metric="revenue",
            unit="EGP",
            value=float("nan"),
            status=BenchmarkDataStatus.OBSERVED,
            evidence="source-1",
            observed_at=datetime.now(timezone.utc),
        )


def test_observation_requires_evidence():
    with pytest.raises(BusinessRuleViolation):
        BenchmarkObservation.create(
            tenant_id=uuid4(),
            definition_id=uuid4(),
            peer_group="faisal-cafes",
            metric="revenue",
            unit="EGP",
            value=1000,
            status=BenchmarkDataStatus.OBSERVED,
            evidence="",
            observed_at=datetime.now(timezone.utc),
        )


def test_observation_creation():
    tenant_id = uuid4()
    definition_id = uuid4()

    observation = BenchmarkObservation.create(
        tenant_id=tenant_id,
        definition_id=definition_id,
        peer_group="faisal-cafes",
        metric="revenue",
        unit="EGP",
        value=1250,
        status=BenchmarkDataStatus.OBSERVED,
        evidence="source-1",
        observed_at=datetime.now(timezone.utc),
    )

    assert observation.tenant_id == tenant_id
    assert observation.definition_id == definition_id
    assert observation.peer_group == "faisal-cafes"
    assert observation.value == 1250.0
    assert observation.status is BenchmarkDataStatus.OBSERVED


def test_observation_accepts_traceable_evidence_reference():
    tenant_id = uuid4()
    evidence_id = uuid4()

    observation = BenchmarkObservation.create(
        tenant_id=tenant_id,
        definition_id=uuid4(),
        peer_group="faisal-cafes",
        metric="revenue",
        unit="EGP",
        value=100,
        status=BenchmarkDataStatus.OBSERVED,
        evidence="source-100",
        evidence_id=evidence_id,
        observed_at=datetime.now(timezone.utc) - timedelta(minutes=1),
    )

    assert observation.evidence_id == evidence_id


def test_observation_rejects_invalid_evidence_reference():
    with pytest.raises(BusinessRuleViolation, match="evidence_id"):
        BenchmarkObservation.create(
            tenant_id=uuid4(),
            definition_id=uuid4(),
            peer_group="faisal-cafes",
            metric="revenue",
            unit="EGP",
            value=100,
            status=BenchmarkDataStatus.OBSERVED,
            evidence="source-100",
            evidence_id="not-a-uuid",
            observed_at=datetime.now(timezone.utc) - timedelta(minutes=1),
        )
