from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from math import isfinite
from uuid import UUID, uuid4

from app.shared.domain.errors import BusinessRuleViolation


class BenchmarkDataStatus(str, Enum):
    OBSERVED = "observed"
    DERIVED = "derived"
    ESTIMATED = "estimated"


def _number(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise BusinessRuleViolation(f"{name} must be numeric")

    value = float(value)

    if not isfinite(value):
        raise BusinessRuleViolation(f"{name} must be finite")

    return value


@dataclass(frozen=True, slots=True)
class BenchmarkDefinition:
    id: UUID
    tenant_id: UUID
    metric: str
    unit: str
    methodology: str
    source: str
    minimum_observations: int = 3

    @classmethod
    def create(
        cls,
        *,
        tenant_id: UUID,
        metric: str,
        unit: str,
        methodology: str,
        source: str,
        minimum_observations: int = 3,
    ) -> "BenchmarkDefinition":
        if not isinstance(tenant_id, UUID):
            raise BusinessRuleViolation("tenant_id must be a UUID")

        for name, value in (
            ("metric", metric),
            ("unit", unit),
            ("methodology", methodology),
            ("source", source),
        ):
            if not isinstance(value, str) or not value.strip():
                raise BusinessRuleViolation(f"{name} must not be empty")

        if (
            isinstance(minimum_observations, bool)
            or not isinstance(minimum_observations, int)
            or minimum_observations < 2
        ):
            raise BusinessRuleViolation(
                "minimum_observations must be an integer >= 2"
            )

        return cls(
            id=uuid4(),
            tenant_id=tenant_id,
            metric=metric.strip(),
            unit=unit.strip(),
            methodology=methodology.strip(),
            source=source.strip(),
            minimum_observations=minimum_observations,
        )


@dataclass(frozen=True, slots=True)
class BenchmarkObservation:
    id: UUID
    tenant_id: UUID
    definition_id: UUID
    peer_group: str
    metric: str
    unit: str
    value: float
    status: BenchmarkDataStatus
    evidence: str
    evidence_id: UUID | None
    observed_at: datetime

    @classmethod
    def create(
        cls,
        *,
        tenant_id: UUID,
        definition_id: UUID,
        peer_group: str,
        metric: str,
        unit: str,
        value: float,
        status: BenchmarkDataStatus,
        evidence: str,
        observed_at: datetime,
        evidence_id: UUID | None = None,
    ) -> "BenchmarkObservation":
        if not isinstance(tenant_id, UUID):
            raise BusinessRuleViolation("tenant_id must be a UUID")

        if not isinstance(definition_id, UUID):
            raise BusinessRuleViolation("definition_id must be a UUID")

        if not isinstance(peer_group, str) or not peer_group.strip():
            raise BusinessRuleViolation("peer_group must not be empty")

        if not isinstance(metric, str) or not metric.strip():
            raise BusinessRuleViolation("metric must not be empty")

        if not isinstance(unit, str) or not unit.strip():
            raise BusinessRuleViolation("unit must not be empty")

        if not isinstance(status, BenchmarkDataStatus):
            try:
                status = BenchmarkDataStatus(status)
            except (TypeError, ValueError) as exc:
                raise BusinessRuleViolation("invalid benchmark data status") from exc

        if not isinstance(evidence, str) or not evidence.strip():
            raise BusinessRuleViolation("evidence must not be empty")

        if evidence_id is not None and not isinstance(evidence_id, UUID):
            raise BusinessRuleViolation("evidence_id must be a UUID")

        if not isinstance(observed_at, datetime) or observed_at.tzinfo is None:
            raise BusinessRuleViolation(
                "observed_at must be timezone-aware"
            )

        if observed_at > datetime.now(timezone.utc):
            raise BusinessRuleViolation(
                "observed_at cannot be in the future"
            )

        return cls(
            id=uuid4(),
            tenant_id=tenant_id,
            definition_id=definition_id,
            peer_group=peer_group.strip(),
            metric=metric.strip(),
            unit=unit.strip(),
            value=_number(value, "value"),
            status=status,
            evidence=evidence.strip(),
            evidence_id=evidence_id,
            observed_at=observed_at,
        )


@dataclass(frozen=True, slots=True)
class BenchmarkResult:
    tenant_id: UUID
    definition_id: UUID
    peer_group: str
    metric: str
    unit: str
    observation_count: int
    minimum_observations: int
    peer_mean: float
    peer_minimum: float
    peer_maximum: float
    peer_variance: float
    sufficient_data: bool
    evidence_count: int
    generated_at: datetime
