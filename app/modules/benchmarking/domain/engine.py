from __future__ import annotations

from datetime import datetime, timezone
from statistics import fmean
from app.shared.domain.errors import BusinessRuleViolation

from .models import (
    BenchmarkDefinition,
    BenchmarkObservation,
    BenchmarkResult,
)


class BenchmarkEngine:
    """Deterministic benchmark calculation engine.

    The engine never guesses missing data and never produces a
    benchmark result from an insufficient or heterogeneous sample.
    """

    @staticmethod
    def calculate(
        definition: BenchmarkDefinition,
        observations: tuple[BenchmarkObservation, ...],
        *,
        peer_group: str,
    ) -> BenchmarkResult:
        if not isinstance(definition, BenchmarkDefinition):
            raise BusinessRuleViolation("definition must be a BenchmarkDefinition")

        if not isinstance(observations, tuple):
            observations = tuple(observations)

        if not isinstance(peer_group, str) or not peer_group.strip():
            raise BusinessRuleViolation("peer_group must not be empty")

        peer_group = peer_group.strip()

        selected = tuple(
            item
            for item in observations
            if item.peer_group == peer_group
        )

        if not selected:
            raise BusinessRuleViolation(
                "no observations available for peer_group"
            )

        for item in selected:
            if item.tenant_id != definition.tenant_id:
                raise BusinessRuleViolation(
                    "cross-tenant benchmark observation"
                )

            if item.definition_id != definition.id:
                raise BusinessRuleViolation(
                    "observation does not belong to definition"
                )

            if item.metric != definition.metric:
                raise BusinessRuleViolation(
                    "observation metric does not match definition"
                )

            if item.unit != definition.unit:
                raise BusinessRuleViolation(
                    "observation unit does not match definition"
                )

        count = len(selected)

        if count < definition.minimum_observations:
            raise BusinessRuleViolation(
                "insufficient observations for benchmark"
            )

        values = tuple(item.value for item in selected)

        mean = fmean(values)
        minimum = min(values)
        maximum = max(values)

        peer_variance = sum((value - mean) ** 2 for value in values) / count

        return BenchmarkResult(
            tenant_id=definition.tenant_id,
            definition_id=definition.id,
            peer_group=peer_group,
            metric=definition.metric,
            unit=definition.unit,
            observation_count=count,
            minimum_observations=definition.minimum_observations,
            peer_mean=mean,
            peer_minimum=minimum,
            peer_maximum=maximum,
            peer_variance=peer_variance,
            sufficient_data=True,
            evidence_count=sum(
                1 for item in selected if item.evidence_id is not None
            ),
            generated_at=datetime.now(timezone.utc),
        )
