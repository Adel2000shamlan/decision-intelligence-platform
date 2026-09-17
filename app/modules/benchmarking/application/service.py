from __future__ import annotations

from uuid import UUID

from app.modules.intelligence.domain.evidence import Evidence
from app.shared.domain.errors import BusinessRuleViolation

from ..domain.engine import BenchmarkEngine
from ..domain.models import (
    BenchmarkDefinition,
    BenchmarkObservation,
    BenchmarkResult,
)


class BenchmarkingService:
    """Application boundary for evidence-backed benchmarking."""

    def __init__(self, engine: BenchmarkEngine | None = None) -> None:
        self.engine = engine or BenchmarkEngine()

    def calculate(
        self,
        *,
        definition: BenchmarkDefinition,
        observations: tuple[BenchmarkObservation, ...],
        evidence: tuple[Evidence, ...],
        peer_group: str,
    ) -> BenchmarkResult:
        if not isinstance(definition, BenchmarkDefinition):
            raise BusinessRuleViolation(
                "definition must be a BenchmarkDefinition"
            )

        if not isinstance(observations, tuple):
            observations = tuple(observations)

        if not isinstance(evidence, tuple):
            evidence = tuple(evidence)

        evidence_by_id: dict[UUID, Evidence] = {}

        for item in evidence:
            if not isinstance(item, Evidence):
                raise BusinessRuleViolation(
                    "evidence must contain Evidence items"
                )

            if item.tenant_id != definition.tenant_id:
                raise BusinessRuleViolation(
                    "evidence tenant mismatch"
                )

            if not item.traceable:
                raise BusinessRuleViolation(
                    "evidence must be traceable"
                )

            if item.evidence_id in evidence_by_id:
                raise BusinessRuleViolation(
                    "duplicate evidence_id"
                )

            evidence_by_id[item.evidence_id] = item

        for observation in observations:
            if not isinstance(observation, BenchmarkObservation):
                raise BusinessRuleViolation(
                    "observations must contain BenchmarkObservation items"
                )

            if observation.tenant_id != definition.tenant_id:
                raise BusinessRuleViolation(
                    "observation tenant mismatch"
                )

            if observation.evidence_id is None:
                raise BusinessRuleViolation(
                    "evidence reference is required"
                )

            if observation.evidence_id not in evidence_by_id:
                raise BusinessRuleViolation(
                    "evidence reference not found"
                )

        return self.engine.calculate(
            definition,
            observations,
            peer_group=peer_group,
        )
