import pytest
from datetime import datetime, timezone
from uuid import uuid4

from app.modules.intelligence.integration.learning_bridge import (
    DecisionLearningBridge,
)
from app.modules.learning.domain.models import (
    LearningOutcomeType,
)
from app.shared.domain.events import DomainEventEnvelope, EventMetadata


class FakeLearningRepository:
    def __init__(self):
        self.items = []

    def save(self, item):
        self.items.append(item)
        return item

    def get(self, tenant_id, observation_id):
        return next(
            (
                item
                for item in self.items
                if item.tenant_id == tenant_id
                and item.id == observation_id
            ),
            None,
        )

    def list(self, tenant_id, *, decision_id=None, metric=None):
        return tuple(
            item
            for item in self.items
            if item.tenant_id == tenant_id
            and (decision_id is None or item.decision_id == decision_id)
            and (metric is None or item.metric == metric)
        )

    def delete(self, tenant_id, observation_id):
        self.items = [
            item
            for item in self.items
            if not (
                item.tenant_id == tenant_id
                and item.id == observation_id
            )
        ]


class FakeLearningService:
    def __init__(self, repository):
        from app.modules.learning.application import LearningService

        self.service = LearningService(repository)

    def observe(self, **kwargs):
        return self.service.observe(**kwargs)


def make_event(event_type, tenant_id, decision_id):
    now = datetime.now(timezone.utc)
    return DomainEventEnvelope(
        event_id=uuid4(),
        event_type=event_type,
        occurred_at=now,
        aggregate_id=decision_id,
        aggregate_type="Decision",
        aggregate_version=4,
        payload={},
        metadata=EventMetadata(
            correlation_id=uuid4(),
            actor_id=uuid4(),
            tenant_id=tenant_id,
        ),
    )


def test_executed_decision_creates_learning_observation():
    tenant_id = uuid4()
    decision_id = uuid4()
    repository = FakeLearningRepository()
    learning = FakeLearningService(repository)
    bridge = DecisionLearningBridge(learning)

    event = make_event("DecisionExecuted", tenant_id, decision_id)

    bridge.handle(event)

    assert len(repository.items) == 1
    observation = repository.items[0]

    assert observation.tenant_id == tenant_id
    assert observation.decision_id == decision_id
    assert observation.outcome_type is LearningOutcomeType.SUCCESS
    assert observation.metric == "decision.lifecycle.outcome"
    assert observation.source == "decision-domain-event"


def test_rejected_decision_becomes_failure_observation():
    tenant_id = uuid4()
    decision_id = uuid4()
    repository = FakeLearningRepository()
    learning = FakeLearningService(repository)
    bridge = DecisionLearningBridge(learning)

    bridge.handle(
        make_event("DecisionRejected", tenant_id, decision_id)
    )

    assert repository.items[0].outcome_type is LearningOutcomeType.FAILURE


def test_duplicate_event_is_idempotent():
    tenant_id = uuid4()
    decision_id = uuid4()
    repository = FakeLearningRepository()
    learning = FakeLearningService(repository)
    bridge = DecisionLearningBridge(learning)

    event = make_event("DecisionExecuted", tenant_id, decision_id)

    bridge.handle(event)
    bridge.handle(event)

    assert len(repository.items) == 1


def test_unrelated_event_is_ignored():
    tenant_id = uuid4()
    decision_id = uuid4()
    repository = FakeLearningRepository()
    learning = FakeLearningService(repository)
    bridge = DecisionLearningBridge(learning)

    bridge.handle(
        make_event("DecisionCreated", tenant_id, decision_id)
    )

    assert repository.items == []


def test_missing_tenant_is_not_recorded():
    tenant_id = uuid4()
    decision_id = uuid4()
    event = make_event("DecisionExecuted", tenant_id, decision_id)

    repository = FakeLearningRepository()
    learning = FakeLearningService(repository)
    bridge = DecisionLearningBridge(learning)

    event_without_tenant = DomainEventEnvelope(
        event_id=event.event_id,
        event_type=event.event_type,
        occurred_at=event.occurred_at,
        aggregate_id=event.aggregate_id,
        aggregate_type=event.aggregate_type,
        aggregate_version=event.aggregate_version,
        payload=event.payload,
        metadata=EventMetadata(
            correlation_id=event.metadata.correlation_id,
            actor_id=event.metadata.actor_id,
            tenant_id=None,
        ),
    )

    bridge.handle(event_without_tenant)

    assert repository.items == []


def test_explicit_tenant_mismatch_is_rejected():
    event_tenant = uuid4()
    other_tenant = uuid4()
    repository = FakeLearningRepository()
    bridge = DecisionLearningBridge(FakeLearningService(repository))

    event = make_event("DecisionExecuted", event_tenant, uuid4())

    with pytest.raises(ValueError, match="does not match"):
        bridge.handle(event, tenant_id=other_tenant)

    assert repository.items == []


def test_non_decision_aggregate_is_rejected():
    tenant_id = uuid4()
    event = make_event("DecisionExecuted", tenant_id, uuid4())

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

    repository = FakeLearningRepository()
    bridge = DecisionLearningBridge(FakeLearningService(repository))

    with pytest.raises(ValueError, match="aggregate_type must be Decision"):
        bridge.handle(event)

    assert repository.items == []
