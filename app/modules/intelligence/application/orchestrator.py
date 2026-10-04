from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.modules.intelligence.application.decision import (
    DecisionIntelligenceInput,
)
from app.modules.intelligence.application.service import (
    IntelligenceApplicationService,
)
from app.modules.intelligence.application.analysis import (
    IntelligenceAnalysisResult,
)
from app.modules.intelligence.integration.learning_bridge import (
    DecisionLearningBridge,
)
from app.modules.intelligence.integration.memory_bridge import (
    DecisionMemoryBridge,
)
from app.shared.domain.events import DomainEventEnvelope


@dataclass(frozen=True, slots=True)
class DecisionIntelligenceOrchestrationResult:
    """
    Result of the decision-intelligence orchestration boundary.

    Intelligence analyzes and returns evidence/confidence, while
    approval and execution remain outside this boundary.
    """

    analysis: IntelligenceAnalysisResult
    memory_integrated: bool = False
    learning_integrated: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.analysis, IntelligenceAnalysisResult):
            raise ValueError("analysis must be IntelligenceAnalysisResult")
        if not isinstance(self.memory_integrated, bool):
            raise ValueError("memory_integrated must be bool")
        if not isinstance(self.learning_integrated, bool):
            raise ValueError("learning_integrated must be bool")


class DecisionIntelligenceOrchestrator:
    """
    Coordinates decision intelligence with event-driven integrations.

    This boundary:
      - analyzes decisions;
      - optionally forwards authoritative events to Memory;
      - optionally forwards outcome events to Learning.

    This boundary never:
      - approves;
      - rejects;
      - executes;
      - closes;
      - changes decision lifecycle state.
    """

    def __init__(
        self,
        intelligence: IntelligenceApplicationService | None = None,
        memory: DecisionMemoryBridge | None = None,
        learning: DecisionLearningBridge | None = None,
    ) -> None:
        self.intelligence = intelligence or IntelligenceApplicationService()
        self.memory = memory
        self.learning = learning

    def analyze(
        self,
        request: DecisionIntelligenceInput,
        *,
        event: DomainEventEnvelope | None = None,
    ) -> DecisionIntelligenceOrchestrationResult:
        analysis = self.intelligence.analyze_decision(request)

        if not analysis.analysis.human_review_required:
            raise ValueError(
                "decision intelligence orchestration requires human review"
            )

        memory_integrated = False
        learning_integrated = False

        if event is not None:
            self._validate_event(request, event)

            if self.memory is not None and self.memory.can_handle(event.event_type):
                self.memory.handle(event)
                memory_integrated = True

            if self.learning is not None and self.learning.can_handle(event.event_type):
                self.learning.handle(
                    event,
                    tenant_id=request.tenant_id,
                )
                learning_integrated = True

        return DecisionIntelligenceOrchestrationResult(
            analysis=analysis,
            memory_integrated=memory_integrated,
            learning_integrated=learning_integrated,
        )

    @staticmethod
    def _validate_event(
        request: DecisionIntelligenceInput,
        event: DomainEventEnvelope,
    ) -> None:
        if event.aggregate_type != "Decision":
            raise ValueError("event aggregate_type must be Decision")

        if not isinstance(event.aggregate_id, UUID):
            raise ValueError("decision event aggregate_id must be UUID")

        event_tenant = event.metadata.tenant_id
        if event_tenant is not None and event_tenant != request.tenant_id:
            raise ValueError(
                "event tenant_id does not match request tenant_id"
            )


def build_decision_context(
    request,
    *,
    knowledge=None,
    knowledge_graph=None,
    memory=None,
    risk=None,
    scenario=None,
    forecasting=None,
):
    from app.modules.intelligence.context.assembler import DecisionContextAssembler

    return DecisionContextAssembler(
        knowledge=knowledge,
        knowledge_graph=knowledge_graph,
        memory=memory,
        risk=risk,
        scenario=scenario,
        forecasting=forecasting,
    ).assemble(request)
