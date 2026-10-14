from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.modules.intelligence.domain.confidence import Confidence
from app.modules.intelligence.domain.evidence import Evidence
from app.modules.intelligence.domain.result import IntelligenceResult
from app.modules.intelligence.domain.scoring import (
    DeterministicScoringEngine,
    ScoreFactor,
)


@dataclass(frozen=True, slots=True)
class ScenarioIntelligenceInput:
    tenant_id: UUID
    actor_id: UUID
    correlation_id: UUID
    evidence: tuple[Evidence, ...]
    factors: tuple[ScoreFactor, ...]
    confirmed_facts: tuple[str, ...]
    assumptions: tuple[str, ...] = ()
    estimates: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for name in ("tenant_id", "actor_id", "correlation_id"):
            if not isinstance(getattr(self, name), UUID):
                raise ValueError(f"{name} must be UUID")

        if not self.evidence:
            raise ValueError("at least one evidence item is required")

        if not isinstance(self.evidence, tuple):
            raise ValueError("evidence must be immutable tuple")

        if not all(isinstance(item, Evidence) for item in self.evidence):
            raise ValueError("evidence must contain Evidence items")

        if not isinstance(self.factors, tuple) or not self.factors:
            raise ValueError("at least one scoring factor is required")

        for name in ("confirmed_facts", "assumptions", "estimates"):
            if not isinstance(getattr(self, name), tuple):
                raise ValueError(f"{name} must be immutable tuple")


class ScenarioIntelligenceService:
    """Deterministic scenario analysis over supplied evidence."""

    def __init__(
        self,
        scoring: DeterministicScoringEngine | None = None,
    ) -> None:
        self.scoring = scoring or DeterministicScoringEngine()

    def analyze(
        self,
        request: ScenarioIntelligenceInput,
    ) -> IntelligenceResult:
        score = self.scoring.calculate(request.factors)

        confidence_basis = (
            f"{len(request.evidence)} evidence item(s), "
            f"{len(request.confirmed_facts)} confirmed fact(s), "
            f"{len(request.assumptions)} assumption(s), "
            f"{len(request.estimates)} estimate(s)"
        )

        return IntelligenceResult(
            tenant_id=request.tenant_id,
            actor_id=request.actor_id,
            correlation_id=request.correlation_id,
            result=score,
            evidence=request.evidence,
            confidence=Confidence(
                value=self._confidence(request),
                basis=confidence_basis,
            ),
            confirmed_facts=request.confirmed_facts,
            assumptions=request.assumptions,
            estimates=request.estimates,
            human_review_required=True,
        )

    @staticmethod
    def _confidence(request: ScenarioIntelligenceInput) -> float:
        evidence_score = min(len(request.evidence) / 5.0, 1.0)
        confirmed_score = min(len(request.confirmed_facts) / 5.0, 1.0)

        uncertainty = len(request.assumptions) + len(request.estimates)
        uncertainty_penalty = min(uncertainty / 10.0, 0.5)

        return max(
            0.0,
            min(
                1.0,
                ((evidence_score + confirmed_score) / 2.0)
                - uncertainty_penalty,
            ),
        )
