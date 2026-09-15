from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.modules.authorization.domain.models import AuthorizationContext
from app.modules.intelligence.application.approval import (
    HumanApprovalGate,
    HumanApprovalGateResult,
)
from app.modules.intelligence.application.decision import (
    DecisionIntelligenceInput,
    DecisionIntelligenceService,
)
from app.modules.intelligence.application.risk import (
    RiskIntelligenceInput,
    RiskIntelligenceService,
)
from app.modules.intelligence.application.scenario import (
    ScenarioIntelligenceInput,
    ScenarioIntelligenceService,
)
from app.modules.intelligence.domain.result import IntelligenceResult


@dataclass(frozen=True, slots=True)
class IntelligenceAnalysisResult:
    analysis: IntelligenceResult
    approval: HumanApprovalGateResult | None = None
    approval_context_present: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.analysis, IntelligenceResult):
            raise ValueError("analysis must be IntelligenceResult")

        if self.approval is not None and not isinstance(
            self.approval,
            HumanApprovalGateResult,
        ):
            raise ValueError("approval must be HumanApprovalGateResult")

        if not isinstance(self.approval_context_present, bool):
            raise ValueError("approval_context_present must be bool")


class IntelligenceAnalysisService:
    """Coordinates intelligence analysis without approving or executing decisions."""

    def __init__(
        self,
        decision: DecisionIntelligenceService | None = None,
        scenario: ScenarioIntelligenceService | None = None,
        risk: RiskIntelligenceService | None = None,
        approval: HumanApprovalGate | None = None,
    ) -> None:
        self.decision = decision or DecisionIntelligenceService()
        self.scenario = scenario or ScenarioIntelligenceService()
        self.risk = risk or RiskIntelligenceService()
        self.approval = approval or HumanApprovalGate()

    def analyze_decision(
        self,
        request: DecisionIntelligenceInput,
    ) -> IntelligenceAnalysisResult:
        return IntelligenceAnalysisResult(
            analysis=self.decision.analyze(request),
        )

    def analyze_scenario(
        self,
        request: ScenarioIntelligenceInput,
    ) -> IntelligenceAnalysisResult:
        return IntelligenceAnalysisResult(
            analysis=self.scenario.analyze(request),
        )

    def analyze_risk(
        self,
        request: RiskIntelligenceInput,
    ) -> IntelligenceAnalysisResult:
        return IntelligenceAnalysisResult(
            analysis=self.risk.analyze(request),
        )

    def evaluate_approval(
        self,
        analysis: IntelligenceAnalysisResult,
        context: AuthorizationContext,
    ) -> IntelligenceAnalysisResult:
        approval = self.approval.evaluate(context)

        return IntelligenceAnalysisResult(
            analysis=analysis.analysis,
            approval=approval,
            approval_context_present=True,
        )
