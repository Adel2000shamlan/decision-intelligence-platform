from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.modules.intelligence.application.decision import (
    DecisionIntelligenceInput,
    DecisionIntelligenceService,
)
from app.modules.intelligence.application.orchestrator import (
    DecisionIntelligenceOrchestrator,
)
from app.modules.intelligence.application.service import (
    IntelligenceApplicationService,
)
from app.modules.intelligence.domain.evidence import Evidence, EvidenceType
from app.modules.intelligence.domain.scoring import ScoreFactor
from app.modules.intelligence.integration.learning_bridge import (
    DecisionLearningBridge,
)
from app.modules.learning.application import (
    LearningFeedbackService,
    LearningService,
)
from app.modules.learning.persistence.sqlite import SQLiteLearningRepository
from app.shared.domain.events import DomainEventEnvelope, EventMetadata


class RecordingIntelligence:
    """Records the exact input passed to the real analysis service."""

    def __init__(self):
        self.delegate = IntelligenceApplicationService()
        self.requests = []

    def analyze_decision(self, request):
        self.requests.append(request)
        return self.delegate.analyze_decision(request)


def make_request(tenant_id):
    return DecisionIntelligenceInput(
        tenant_id=tenant_id,
        actor_id=uuid4(),
        correlation_id=uuid4(),
        evidence=(
            Evidence(
                evidence_id=uuid4(),
                tenant_id=tenant_id,
                evidence_type=EvidenceType.FACT,
                source="acceptance-test",
                reference="acceptance:confirmed-fact",
                statement="Confirmed evidence for the decision",
            ),
        ),
        factors=(
            ScoreFactor(name="market", value=0.8, weight=1.0),
            ScoreFactor(name="risk", value=0.6, weight=1.0),
        ),
        confirmed_facts=("Confirmed input fact",),
    )


def make_outcome_event(tenant_id, decision_id):
    return DomainEventEnvelope(
        event_id=uuid4(),
        event_type="DecisionOutcomeRecorded",
        occurred_at=datetime.now(timezone.utc),
        aggregate_id=decision_id,
        aggregate_type="Decision",
        aggregate_version=1,
        payload={
            "outcome_type": "success",
            "metric": "revenue",
            "expected_value": 100.0,
            "actual_value": 120.0,
            "notes": "Acceptance-test outcome",
            "confidence": 0.9,
        },
        metadata=EventMetadata(
            correlation_id=uuid4(),
            actor_id=uuid4(),
            tenant_id=tenant_id,
        ),
    )


def test_outcome_feedback_reaches_real_analysis_as_observation():
    tenant_id = uuid4()
    request = make_request(tenant_id)
    repository = SQLiteLearningRepository()

    learning_service = LearningService(repository)
    feedback_service = LearningFeedbackService(repository)
    bridge = DecisionLearningBridge(learning_service)

    # Step 1: record an authoritative outcome as a learning observation.
    outcome_event = make_outcome_event(tenant_id, uuid4())
    bridge.handle(outcome_event)

    # Step 2: establish the original deterministic score.
    baseline = DecisionIntelligenceService().analyze(request)

    # Step 3: run the actual orchestrator with feedback enabled.
    recording_intelligence = RecordingIntelligence()
    orchestrator = DecisionIntelligenceOrchestrator(
        intelligence=recording_intelligence,
        learning_feedback=feedback_service,
    )

    result = orchestrator.analyze_with_learning_feedback(
        request,
        metric="revenue",
    )

    # Step 4: prove the enriched request reached the real analysis service.
    assert len(recording_intelligence.requests) == 1
    enriched_request = recording_intelligence.requests[0]
    assert len(enriched_request.evidence) == len(request.evidence) + 1

    feedback_evidence = enriched_request.evidence[-1]
    assert feedback_evidence.evidence_type is EvidenceType.OBSERVATION
    assert feedback_evidence.source == "learning-feedback"
    assert feedback_evidence.tenant_id == tenant_id
    assert feedback_evidence.traceable is True
    assert "revenue" in feedback_evidence.statement
    assert str(outcome_event.event_id) in feedback_evidence.statement

    # Step 5: feedback does not change the deterministic score.
    assert result.analysis.analysis.result == baseline.result

    # Step 6: human review remains mandatory.
    assert result.analysis.analysis.human_review_required is True

    # The orchestrator only analyzes; it does not approve or execute.
    assert result.analysis.approval is None
    assert result.analysis.approval_context_present is False

    repository.connection.close()


def test_feedback_analysis_requires_configured_feedback_service():
    tenant_id = uuid4()
    orchestrator = DecisionIntelligenceOrchestrator()

    with pytest.raises(
        ValueError,
        match="learning_feedback service is required",
    ):
        orchestrator.analyze_with_learning_feedback(
            make_request(tenant_id),
            metric="revenue",
        )


def test_feedback_service_only_returns_observations_for_its_tenant():
    tenant_id = uuid4()
    other_tenant_id = uuid4()
    repository = SQLiteLearningRepository()
    learning_service = LearningService(repository)
    bridge = DecisionLearningBridge(learning_service)

    bridge.handle(make_outcome_event(tenant_id, uuid4()))
    bridge.handle(make_outcome_event(other_tenant_id, uuid4()))

    feedback = LearningFeedbackService(repository).build(
        tenant_id,
        metric="revenue",
    )

    assert feedback.tenant_id == tenant_id
    assert feedback.observation_count == 1
    assert all(
        observation.tenant_id == tenant_id
        for observation in feedback.observations
    )

    repository.connection.close()
