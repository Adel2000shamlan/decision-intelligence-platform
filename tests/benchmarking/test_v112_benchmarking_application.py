from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from app.modules.benchmarking.application.service import BenchmarkingService
from app.modules.benchmarking.domain.models import (
    BenchmarkDataStatus,
    BenchmarkDefinition,
    BenchmarkObservation,
)
from app.modules.intelligence.domain.evidence import Evidence, EvidenceType
from app.shared.domain.errors import BusinessRuleViolation


def make_definition(tenant_id):
    return BenchmarkDefinition.create(
        tenant_id=tenant_id,
        metric="revenue",
        unit="EGP",
        methodology="peer mean",
        source="verified peer data",
        minimum_observations=2,
    )


def make_evidence(tenant_id, evidence_id=None, traceable=True):
    return Evidence(
        evidence_id=evidence_id or uuid4(),
        tenant_id=tenant_id,
        evidence_type=EvidenceType.OBSERVATION,
        source="verified-source",
        reference="benchmark-001",
        statement="Verified peer revenue observation",
        traceable=traceable,
    )


def make_observation(
    tenant_id,
    definition_id,
    value,
    evidence_id,
):
    return BenchmarkObservation.create(
        tenant_id=tenant_id,
        definition_id=definition_id,
        peer_group="faisal-cafes",
        metric="revenue",
        unit="EGP",
        value=value,
        status=BenchmarkDataStatus.OBSERVED,
        evidence="verified-source",
        evidence_id=evidence_id,
        observed_at=datetime.now(timezone.utc) - timedelta(minutes=1),
    )


def test_service_calculates_benchmark_from_verified_evidence():
    tenant_id = uuid4()
    definition = make_definition(tenant_id)

    evidence_1 = make_evidence(tenant_id)
    evidence_2 = make_evidence(tenant_id)

    observations = (
        make_observation(
            tenant_id,
            definition.id,
            1000,
            evidence_1.evidence_id,
        ),
        make_observation(
            tenant_id,
            definition.id,
            2000,
            evidence_2.evidence_id,
        ),
    )

    result = BenchmarkingService().calculate(
        definition=definition,
        observations=observations,
        evidence=(evidence_1, evidence_2),
        peer_group="faisal-cafes",
    )

    assert result.sufficient_data is True
    assert result.observation_count == 2
    assert result.peer_mean == pytest.approx(1500.0)
    assert result.evidence_count == 2


def test_service_rejects_missing_evidence_reference():
    tenant_id = uuid4()
    definition = make_definition(tenant_id)

    observation = make_observation(
        tenant_id,
        definition.id,
        1000,
        uuid4(),
    )

    with pytest.raises(
        BusinessRuleViolation,
        match="evidence reference",
    ):
        BenchmarkingService().calculate(
            definition=definition,
            observations=(observation,),
            evidence=(),
            peer_group="faisal-cafes",
        )


def test_service_rejects_cross_tenant_evidence():
    tenant_id = uuid4()
    foreign_tenant_id = uuid4()
    definition = make_definition(tenant_id)

    evidence = make_evidence(foreign_tenant_id)

    observation = make_observation(
        tenant_id,
        definition.id,
        1000,
        evidence.evidence_id,
    )

    with pytest.raises(
        BusinessRuleViolation,
        match="evidence tenant mismatch",
    ):
        BenchmarkingService().calculate(
            definition=definition,
            observations=(observation,),
            evidence=(evidence,),
            peer_group="faisal-cafes",
        )


def test_service_rejects_untraceable_evidence():
    tenant_id = uuid4()
    definition = make_definition(tenant_id)

    evidence = make_evidence(tenant_id, traceable=False)

    observation = make_observation(
        tenant_id,
        definition.id,
        1000,
        evidence.evidence_id,
    )

    with pytest.raises(
        BusinessRuleViolation,
        match="traceable",
    ):
        BenchmarkingService().calculate(
            definition=definition,
            observations=(observation,),
            evidence=(evidence,),
            peer_group="faisal-cafes",
        )


def test_service_rejects_non_evidence_items():
    tenant_id = uuid4()
    definition = make_definition(tenant_id)

    observation = make_observation(
        tenant_id,
        definition.id,
        1000,
        uuid4(),
    )

    with pytest.raises(
        BusinessRuleViolation,
        match="Evidence",
    ):
        BenchmarkingService().calculate(
            definition=definition,
            observations=(observation,),
            evidence=("not-evidence",),
            peer_group="faisal-cafes",
        )


def test_service_rejects_insufficient_observations_before_result():
    tenant_id = uuid4()
    definition = make_definition(tenant_id)

    evidence = make_evidence(tenant_id)

    observation = make_observation(
        tenant_id,
        definition.id,
        1000,
        evidence.evidence_id,
    )

    with pytest.raises(
        BusinessRuleViolation,
        match="insufficient observations",
    ):
        BenchmarkingService().calculate(
            definition=definition,
            observations=(observation,),
            evidence=(evidence,),
            peer_group="faisal-cafes",
        )
