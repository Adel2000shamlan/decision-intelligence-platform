from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4

from app.infrastructure.events import EventBus, EventStore
from app.shared.integration.events import (
    EventBusDomainEventPublisher,
    envelope_from_event,
)


class SampleStatus(str, Enum):
    ACTIVE = "active"


@dataclass(frozen=True)
class SampleEvent:
    event_id: object
    occurred_at: datetime
    aggregate_id: object
    actor_id: object
    title: str
    status: SampleStatus


def make_event():
    return SampleEvent(
        event_id=uuid4(),
        occurred_at=datetime.now(timezone.utc),
        aggregate_id=uuid4(),
        actor_id=uuid4(),
        title="integration-test",
        status=SampleStatus.ACTIVE,
    )


def test_event_is_enveloped_with_context():
    event = make_event()
    correlation_id = uuid4()
    tenant_id = uuid4()

    envelope = envelope_from_event(
        event,
        "Sample",
        7,
        correlation_id=correlation_id,
        tenant_id=tenant_id,
    )

    assert envelope.event_id == event.event_id
    assert envelope.event_type == "SampleEvent"
    assert envelope.aggregate_id == event.aggregate_id
    assert envelope.aggregate_type == "Sample"
    assert envelope.aggregate_version == 7
    assert envelope.metadata.correlation_id == correlation_id
    assert envelope.metadata.tenant_id == tenant_id
    assert envelope.metadata.actor_id == event.actor_id


def test_adapter_publishes_transport_safe_event():
    event = make_event()
    bus = EventBus()
    store = EventStore()
    publisher = EventBusDomainEventPublisher(bus, store)

    envelope = envelope_from_event(
        event,
        "Sample",
        3,
        tenant_id=uuid4(),
    )

    publisher.publish(envelope)

    stored = store.all()
    assert len(stored) == 1
    assert stored[0].event_id == str(event.event_id)
    assert stored[0].event_type == "SampleEvent"
    assert stored[0].aggregate_id == str(event.aggregate_id)
    assert stored[0].payload["payload"]["status"] == "active"
    assert stored[0].payload["payload"]["aggregate_id"] == str(event.aggregate_id)
    assert stored[0].payload["aggregate_version"] == 3


def test_duplicate_event_is_idempotent_when_store_is_present():
    event = make_event()
    bus = EventBus()
    store = EventStore()
    publisher = EventBusDomainEventPublisher(bus, store)

    envelope = envelope_from_event(event, "Sample", 1)

    publisher.publish(envelope)
    publisher.publish(envelope)

    assert len(store.all()) == 1


def test_adapter_can_publish_without_event_store():
    event = make_event()
    bus = EventBus()
    publisher = EventBusDomainEventPublisher(bus)

    envelope = envelope_from_event(event, "Sample", 1)

    publisher.publish(envelope)
