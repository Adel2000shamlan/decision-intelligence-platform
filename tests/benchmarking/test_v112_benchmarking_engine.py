from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from app.modules.benchmarking.domain.engine import BenchmarkEngine
from app.modules.benchmarking.domain.models import (
    BenchmarkDataStatus,
    BenchmarkDefinition,
    BenchmarkObservation,
)
from app.shared.domain.errors import BusinessRuleViolation


def make_definition(
    tenant_id,
    *,
    minimum_observations=3,
    metric="revenue",
    unit="EGP",
):
    return BenchmarkDefinition.create(
        tenant_id=tenant_id,
        metric=metric,
        unit=unit,
        methodology="peer mean",
        source="verified-source",
        minimum_observations=minimum_observations,
    )


def make_observation(
    tenant_id,
    definition_id,
    value,
    *,
    peer_group="faisal-cafes",
    metric="revenue",
    unit="EGP",
    evidence_id=None,
):
    return BenchmarkObservation.create(
        tenant_id=tenant_id,
        definition_id=definition_id,
        peer_group=peer_group,
        metric=metric,
        unit=unit,
        value=value,
        status=BenchmarkDataStatus.OBSERVED,
        evidence=f"source-{value}",
        evidence_id=evidence_id,
        observed_at=datetime.now(timezone.utc) - timedelta(minutes=1),
    )


def test_engine_requires_sufficient_observations():
    tenant_id = uuid4()
    definition = make_definition(tenant_id, minimum_observations=3)

    observations = (
        make_observation(tenant_id, definition.id, 100),
        make_observation(tenant_id, definition.id, 200),
    )

    with pytest.raises(BusinessRuleViolation, match="insufficient"):
        BenchmarkEngine.calculate(
            definition,
            observations,
            peer_group="faisal-cafes",
        )


def test_engine_calculates_deterministic_peer_statistics():
    tenant_id = uuid4()
    definition = make_definition(tenant_id)

    evidence_ids = (uuid4(), uuid4(), uuid4())

    observations = (
        make_observation(
            tenant_id, definition.id, 100, evidence_id=evidence_ids[0]
        ),
        make_observation(
            tenant_id, definition.id, 200, evidence_id=evidence_ids[1]
        ),
        make_observation(
            tenant_id, definition.id, 300, evidence_id=evidence_ids[2]
        ),
    )

    result = BenchmarkEngine.calculate(
        definition,
        observations,
        peer_group="faisal-cafes",
    )

    assert result.sufficient_data is True
    assert result.observation_count == 3
    assert result.minimum_observations == 3
    assert result.peer_mean == 200.0
    assert result.peer_minimum == 100.0
    assert result.peer_maximum == 300.0
    assert result.peer_variance == pytest.approx(6666.666666666667)
    assert result.evidence_count == 3


def test_engine_ignores_other_peer_groups():
    tenant_id = uuid4()
    definition = make_definition(tenant_id)

    observations = (
        make_observation(tenant_id, definition.id, 100),
        make_observation(tenant_id, definition.id, 200),
        make_observation(tenant_id, definition.id, 300),
        make_observation(
            tenant_id,
            definition.id,
            999,
            peer_group="other-cafes",
        ),
    )

    result = BenchmarkEngine.calculate(
        definition,
        observations,
        peer_group="faisal-cafes",
    )

    assert result.observation_count == 3
    assert result.peer_mean == 200.0


def test_engine_rejects_cross_tenant_observation():
    tenant_id = uuid4()
    foreign_tenant = uuid4()

    definition = make_definition(tenant_id)

    observations = (
        make_observation(tenant_id, definition.id, 100),
        make_observation(tenant_id, definition.id, 200),
        make_observation(foreign_tenant, definition.id, 300),
    )

    with pytest.raises(BusinessRuleViolation, match="cross-tenant"):
        BenchmarkEngine.calculate(
            definition,
            observations,
            peer_group="faisal-cafes",
        )


def test_engine_rejects_metric_mismatch():
    tenant_id = uuid4()
    definition = make_definition(tenant_id)

    observations = (
        make_observation(tenant_id, definition.id, 100),
        make_observation(tenant_id, definition.id, 200),
        make_observation(
            tenant_id,
            definition.id,
            300,
            metric="customers",
        ),
    )

    with pytest.raises(BusinessRuleViolation, match="metric"):
        BenchmarkEngine.calculate(
            definition,
            observations,
            peer_group="faisal-cafes",
        )


def test_engine_rejects_unit_mismatch():
    tenant_id = uuid4()
    definition = make_definition(tenant_id)

    observations = (
        make_observation(tenant_id, definition.id, 100),
        make_observation(tenant_id, definition.id, 200),
        make_observation(
            tenant_id,
            definition.id,
            300,
            unit="USD",
        ),
    )

    with pytest.raises(BusinessRuleViolation, match="unit"):
        BenchmarkEngine.calculate(
            definition,
            observations,
            peer_group="faisal-cafes",
        )


def test_engine_rejects_unknown_peer_group():
    tenant_id = uuid4()
    definition = make_definition(tenant_id)

    observations = (
        make_observation(tenant_id, definition.id, 100),
        make_observation(tenant_id, definition.id, 200),
        make_observation(tenant_id, definition.id, 300),
    )

    with pytest.raises(BusinessRuleViolation, match="no observations"):
        BenchmarkEngine.calculate(
            definition,
            observations,
            peer_group="unknown-group",
        )


def test_engine_rejects_observation_from_different_definition():
    tenant_id = uuid4()
    definition = make_definition(tenant_id)
    other_definition = make_definition(tenant_id)

    observations = (
        make_observation(tenant_id, definition.id, 100),
        make_observation(tenant_id, definition.id, 200),
        make_observation(tenant_id, other_definition.id, 300),
    )

    with pytest.raises(
        BusinessRuleViolation,
        match="does not belong to definition",
    ):
        BenchmarkEngine.calculate(
            definition,
            observations,
            peer_group="faisal-cafes",
        )
