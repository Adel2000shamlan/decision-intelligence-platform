from __future__ import annotations

from datetime import datetime
from uuid import UUID

from ..domain.models import (
    BenchmarkDataStatus,
    BenchmarkDefinition,
    BenchmarkObservation,
)


def definition_from_row(row) -> BenchmarkDefinition:
    return BenchmarkDefinition(
        id=UUID(str(row["id"])),
        tenant_id=UUID(str(row["tenant_id"])),
        metric=row["metric"],
        unit=row["unit"],
        methodology=row["methodology"],
        source=row["source"],
        minimum_observations=row["minimum_observations"],
    )


def definition_to_row(
    definition: BenchmarkDefinition,
) -> tuple:
    return (
        definition.id,
        definition.tenant_id,
        definition.metric,
        definition.unit,
        definition.methodology,
        definition.source,
        definition.minimum_observations,
    )


def observation_from_row(row) -> BenchmarkObservation:
    return BenchmarkObservation(
        id=UUID(str(row["id"])),
        tenant_id=UUID(str(row["tenant_id"])),
        definition_id=UUID(str(row["definition_id"])),
        peer_group=row["peer_group"],
        metric=row["metric"],
        unit=row["unit"],
        value=float(row["value"]),
        status=BenchmarkDataStatus(row["status"]),
        evidence=row["evidence"],
        evidence_id=(
            UUID(str(row["evidence_id"]))
            if row["evidence_id"] is not None
            else None
        ),
        observed_at=(
            row["observed_at"]
            if isinstance(row["observed_at"], datetime)
            else datetime.fromisoformat(row["observed_at"])
        ),
    )


def observation_to_row(
    observation: BenchmarkObservation,
) -> tuple:
    return (
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
