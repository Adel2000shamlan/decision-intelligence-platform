from datetime import datetime, timezone
from uuid import uuid4

from app.modules.intelligence.integration.memory_bridge import (
    DecisionMemoryBridge,
)
from app.modules.memory.application.service import MemoryService
from app.modules.memory.domain.models import MemoryType
from app.shared.domain.events import DomainEventEnvelope, EventMetadata


class FakeMemoryRepository:
    def __init__(self):
        self.items = []

    def save(self, item):
        self.items.append(item)
        return item

    def get(self, tenant_id, memory_id):
        return next(
            (
                item
                for item in self.items
                if item.tenant_id == tenant_id and item.id == memory_id
            ),
            None,
        )

    def list(self, tenant_id, *, memory_type=None, status=None):
        return tuple(
            item
            for item in self.items
            if item.tenant_id == tenant_id
            and (memory_type is None or item.memory_type is memory_type)
            and (status is None or item.status is status)
        )

    def delete(self, tenant_id, memory_id):
        self.items = [
            item
            for item in self.items
            if not (item.tenant_id == tenant_id and item.id == memory_id)
        ]


class FakeMemoryService:
    def __init__(self, repository):
        self.service = MemoryService(repository)

    def remember(self, **kwargs):
        return self.service.remember(**kwargs)


def make_event(event_type, tenant_id, decision_id):
    return DomainEventEnvelope(
        event_id=uuid4(),
        event_type=event_type,
        occurred_at=datetime.now(timezone.utc),
        aggregate_id=decision_id,
        aggregate_type="Decision",
        aggregate_version=4,
        payload={"event": event_type},
        metadata=EventMetadata(
            correlation_id=uuid4(),
            actor_id=uuid4(),
            tenant_id=tenant_id,
        ),
    )


def test_created_decision_is_stored_as_decision_memory():
    tenant_id = uuid4()
    repository = FakeMemoryRepository()
    bridge = DecisionMemoryBridge(FakeMemoryService(repository))

    bridge.handle(make_event("DecisionCreated", tenant_id, uuid4()))

    assert len(repository.items) == 1
    assert repository.items[0].tenant_id == tenant_id
    assert repository.items[0].memory_type is MemoryType.DECISION
    assert repository.items[0].source == "decision-domain-event"


def test_rejected_decision_is_stored_as_observation():
    tenant_id = uuid4()
    repository = FakeMemoryRepository()
    bridge = DecisionMemoryBridge(FakeMemoryService(repository))

    bridge.handle(make_event("DecisionRejected", tenant_id, uuid4()))

    assert repository.items[0].memory_type is MemoryType.OBSERVATION


def test_unrelated_event_is_ignored():
    tenant_id = uuid4()
    repository = FakeMemoryRepository()
    bridge = DecisionMemoryBridge(FakeMemoryService(repository))

    bridge.handle(make_event("DecisionAnalysisStarted", tenant_id, uuid4()))

    assert repository.items == []


def test_duplicate_event_is_idempotent():
    tenant_id = uuid4()
    repository = FakeMemoryRepository()
    bridge = DecisionMemoryBridge(FakeMemoryService(repository))

    event = make_event("DecisionExecuted", tenant_id, uuid4())

    bridge.handle(event)
    bridge.handle(event)

    assert len(repository.items) == 1


def test_missing_tenant_is_ignored():
    tenant_id = uuid4()
    event = make_event("DecisionClosed", tenant_id, uuid4())

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

    repository = FakeMemoryRepository()
    bridge = DecisionMemoryBridge(FakeMemoryService(repository))

    bridge.handle(event_without_tenant)

    assert repository.items == []


def test_non_decision_aggregate_is_rejected():
    tenant_id = uuid4()
    event = make_event("DecisionCreated", tenant_id, uuid4())

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

    repository = FakeMemoryRepository()
    bridge = DecisionMemoryBridge(FakeMemoryService(repository))

    import pytest

    with pytest.raises(ValueError, match="aggregate_type must be Decision"):
        bridge.handle(event)

    assert repository.items == []
