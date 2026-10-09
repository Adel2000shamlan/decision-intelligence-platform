from uuid import uuid4

import pytest

from app.modules.intelligence.application.decision import (
    DecisionIntelligenceInput,
    DecisionIntelligenceService,
)
from app.modules.intelligence.domain.evidence import (
    Evidence,
    EvidenceType,
)
from app.modules.intelligence.domain.scoring import ScoreFactor
from app.modules.intelligence.integration.learning_feedback import (
    LearningFeedbackIntelligenceAdapter,
)
from app.modules.learning.domain.feedback import LearningFeedback
from app.modules.learning.domain.models import (
    LearningObservation,
    LearningOutcomeType,
)


def make_request(tenant_id):
    evidence = Evidence(
        evidence_id=uuid4(),
        tenant_id=tenant_id,
        evidence_type=EvidenceType.FACT,
        source="test",
        reference="test:source",
        statement="Confirmed source evidence",
    )

    return DecisionIntelligenceInput(
        tenant_id=tenant_id,
        actor_id=uuid4(),
        correlation_id=uuid4(),
        evidence=(evidence,),
        factors=(
            ScoreFactor(name="market", value=0.8, weight=1.0),
            ScoreFactor(name="risk", value=0.6, weight=1.0),
        ),
        confirmed_facts=("Confirmed fact",),
    )


def make_feedback(tenant_id):
    observation = LearningObservation.create(
        tenant_id=tenant_id,
        decision_id=uuid4(),
        outcome_type=LearningOutcomeType.SUCCESS,
        metric="revenue",
        source="decision-outcome-event",
        expected_value=100.0,
        actual_value=120.0,
        confidence=0.9,
    )

    return LearningFeedback.from_observations(
        tenant_id=tenant_id,
        metric="revenue",
        observations=(observation,),
    )


def test_learning_feedback_becomes_traceable_observation():
    tenant_id = uuid4()
    request = make_request(tenant_id)
    feedback = make_feedback(tenant_id)

    enriched = LearningFeedbackIntelligenceAdapter().enrich(
        request,
        feedback,
    )

    assert len(enriched.evidence) == 2

    learned = enriched.evidence[-1]

    assert learned.evidence_type is EvidenceType.OBSERVATION
    assert learned.source == "learning-feedback"
    assert learned.tenant_id == tenant_id
    assert learned.traceable is True
    assert "revenue" in learned.statement
    assert learned.reference.startswith("learning-feedback:")


def test_learning_feedback_preserves_deterministic_score():
    tenant_id = uuid4()
    request = make_request(tenant_id)
    feedback = make_feedback(tenant_id)

    service = DecisionIntelligenceService()
    before = service.analyze(request)
    enriched = LearningFeedbackIntelligenceAdapter().enrich(
        request,
        feedback,
    )
    after = service.analyze(enriched)

    assert before.result == after.result
    assert before.human_review_required is True
    assert after.human_review_required is True


def test_learning_feedback_cannot_cross_tenant():
    request_tenant = uuid4()
    feedback_tenant = uuid4()

    with pytest.raises(ValueError, match="tenant_id"):
        LearningFeedbackIntelligenceAdapter().enrich(
            make_request(request_tenant),
            make_feedback(feedback_tenant),
        )


def test_learning_feedback_evidence_is_deterministic():
    tenant_id = uuid4()
    request = make_request(tenant_id)
    feedback = make_feedback(tenant_id)

    adapter = LearningFeedbackIntelligenceAdapter()

    first = adapter.enrich(request, feedback).evidence[-1]
    second = adapter.enrich(request, feedback).evidence[-1]

    assert first.evidence_id == second.evidence_id
    assert first.reference == second.reference
    assert first.statement == second.statement


def test_learning_feedback_evidence_references_source_observations():
    tenant_id = uuid4()
    observation = LearningObservation.create(
        tenant_id=tenant_id,
        decision_id=uuid4(),
        outcome_type=LearningOutcomeType.SUCCESS,
        metric="revenue",
        source="decision-outcome-event",
        expected_value=100.0,
        actual_value=120.0,
        confidence=0.9,
    )
    feedback = LearningFeedback.from_observations(
        tenant_id=tenant_id,
        metric="revenue",
        observations=(observation,),
    )

    learned = LearningFeedbackIntelligenceAdapter().enrich(
        make_request(tenant_id),
        feedback,
    ).evidence[-1]

    assert str(observation.id) in learned.reference
    assert str(observation.id) in learned.statement
    assert learned.traceable is True
