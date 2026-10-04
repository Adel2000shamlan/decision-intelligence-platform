from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.modules.intelligence.application.decision import (
    DecisionIntelligenceInput,
)
from app.modules.intelligence.application.orchestrator import (
    DecisionIntelligenceOrchestrationResult,
    DecisionIntelligenceOrchestrator,
)
from app.modules.intelligence.domain.evidence import (
    Evidence,
    EvidenceType,
)
from app.modules.intelligence.domain.scoring import ScoreFactor
from app.shared.domain.events import DomainEventEnvelope, EventMetadata


class FakeMemoryBridge:
    def __init__(self):
        self.events = []

    def can_handle(self, event_type):
        return event_type in {"DecisionCreated", "DecisionExecuted"}

    def handle(self, event):
        self.events.append(event)


class FakeLearningBridge:
    def __init__(self):
        self.events = []

    def can_handle(self, event_type):
        return event_type in {
            "DecisionExecuted",
            "DecisionRejected",
            "DecisionCancelled",
            "DecisionClosed",
        }

    def handle(self, event, *, tenant_id=None):
        self.events.append((event, tenant_id))


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
                source="test",
                reference="test-reference",
                statement="confirmed evidence",
            ),
        ),
        factors=(
            ScoreFactor(
                name="quality",
                value=0.8,
                weight=1.0,
            ),
        ),
        confirmed_facts=("fact-1",),
    )


def make_event(tenant_id, event_type="DecisionCreated"):
    return DomainEventEnvelope(
        event_id=uuid4(),
        event_type=event_type,
        occurred_at=datetime.now(timezone.utc),
        aggregate_id=uuid4(),
        aggregate_type="Decision",
        aggregate_version=1,
        payload={"event": event_type},
        metadata=EventMetadata(
            correlation_id=uuid4(),
            actor_id=uuid4(),
            tenant_id=tenant_id,
        ),
    )


def test_orchestrator_returns_human_review_required_analysis():
    tenant_id = uuid4()

    result = DecisionIntelligenceOrchestrator().analyze(
        make_request(tenant_id)
    )

    assert isinstance(result, DecisionIntelligenceOrchestrationResult)
    assert result.analysis.analysis.human_review_required is True
    assert result.memory_integrated is False
    assert result.learning_integrated is False


def test_orchestrator_integrates_authoritative_event():
    tenant_id = uuid4()
    memory = FakeMemoryBridge()
    learning = FakeLearningBridge()

    orchestrator = DecisionIntelligenceOrchestrator(
        memory=memory,
        learning=learning,
    )

    event = make_event(tenant_id, "DecisionExecuted")

    result = orchestrator.analyze(
        make_request(tenant_id),
        event=event,
    )

    assert result.memory_integrated is True
    assert result.learning_integrated is True
    assert memory.events == [event]
    assert learning.events == [(event, tenant_id)]


def test_orchestrator_does_not_integrate_without_event():
    memory = FakeMemoryBridge()
    learning = FakeLearningBridge()

    result = DecisionIntelligenceOrchestrator(
        memory=memory,
        learning=learning,
    ).analyze(make_request(uuid4()))

    assert result.memory_integrated is False
    assert result.learning_integrated is False
    assert memory.events == []
    assert learning.events == []


def test_orchestrator_rejects_non_reviewable_intelligence_result():
    class UnsafeIntelligence:
        def analyze_decision(self, request):
            class Analysis:
                class Inner:
                    human_review_required = False

                analysis = Inner()

            return Analysis()

    with pytest.raises(
        ValueError,
        match="requires human review",
    ):
        DecisionIntelligenceOrchestrator(
            intelligence=UnsafeIntelligence()
        ).analyze(make_request(uuid4()))


def test_learning_receives_request_tenant():
    tenant_id = uuid4()
    learning = FakeLearningBridge()

    DecisionIntelligenceOrchestrator(
        learning=learning,
    ).analyze(
        make_request(tenant_id),
        event=make_event(tenant_id, "DecisionRejected"),
    )

    assert learning.events[0][1] == tenant_id


def test_event_tenant_mismatch_is_rejected():
    request_tenant = uuid4()
    event_tenant = uuid4()

    with pytest.raises(
        ValueError,
        match="does not match request tenant_id",
    ):
        DecisionIntelligenceOrchestrator().analyze(
            make_request(request_tenant),
            event=make_event(event_tenant, "DecisionCreated"),
        )


def test_orchestrator_rejects_non_decision_aggregate_event():
    tenant_id = uuid4()
    event = make_event(tenant_id, "DecisionExecuted")

    event = DomainEventEnvelope(
        event_id=event.event_id,
        event_type=event.event_type,
        occurred_at=event.occurred_at,
        aggregate_id=event.aggregate_id,
        aggregate_type="Project",
        aggregate_version=event.aggregate_version,
        payload=event.payload,
        metadata=event.metadata,
    )

    with pytest.raises(
        ValueError,
        match="aggregate_type must be Decision",
    ):
        DecisionIntelligenceOrchestrator().analyze(
            make_request(tenant_id),
            event=event,
        )
