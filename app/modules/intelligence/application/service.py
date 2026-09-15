from __future__ import annotations

from app.modules.intelligence.application.analysis import (
    IntelligenceAnalysisResult,
    IntelligenceAnalysisService,
)
from app.modules.intelligence.application.decision import (
    DecisionIntelligenceInput,
)
from app.modules.intelligence.application.risk import (
    RiskIntelligenceInput,
)
from app.modules.intelligence.application.scenario import (
    ScenarioIntelligenceInput,
)


class IntelligenceApplicationService:
    """Public application boundary for V105 intelligence capabilities."""

    def __init__(
        self,
        analysis: IntelligenceAnalysisService | None = None,
    ) -> None:
        self.analysis = analysis or IntelligenceAnalysisService()

    def analyze_decision(
        self,
        request: DecisionIntelligenceInput,
    ) -> IntelligenceAnalysisResult:
        return self.analysis.analyze_decision(request)

    def analyze_scenario(
        self,
        request: ScenarioIntelligenceInput,
    ) -> IntelligenceAnalysisResult:
        return self.analysis.analyze_scenario(request)

    def analyze_risk(
        self,
        request: RiskIntelligenceInput,
    ) -> IntelligenceAnalysisResult:
        return self.analysis.analyze_risk(request)
