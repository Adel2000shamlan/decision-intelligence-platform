from uuid import uuid4

from app.modules.decision.domain.models import (
    Decision,
    DecisionOutcomeRecorded,
    DecisionType,
)
from app.modules.decision.domain.outcome import (
    DecisionOutcome,
    DecisionOutcomeType,
)


def test_decision_records_authoritative_outcome_event():
    decision = Decision.create(
        organization_id=uuid4(),
        project_id=uuid4(),
        title="Outcome test",
        decision_type=DecisionType.STRATEGIC,
    )

    actor_id = uuid4()

    decision.record_outcome(
        DecisionOutcome(
            outcome_type=DecisionOutcomeType.SUCCESS,
            metric="revenue",
            expected_value=100.0,
            actual_value=120.0,
            notes="Observed result",
            confidence=0.95,
        ),
        actor_id=actor_id,
    )

    events = decision.pull_events()

    outcome_events = [
        event for event in events
        if isinstance(event, DecisionOutcomeRecorded)
    ]

    assert len(outcome_events) == 1

    event = outcome_events[0]

    assert event.aggregate_id == decision.id
    assert event.actor_id == actor_id
    assert event.outcome_type == "success"
    assert event.metric == "revenue"
    assert event.expected_value == 100.0
    assert event.actual_value == 120.0
    assert event.notes == "Observed result"
    assert event.confidence == 0.95
