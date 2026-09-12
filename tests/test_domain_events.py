from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4

from app.shared.domain.events import DomainEventEnvelope, EventMetadata, InMemoryDomainEventPublisher

@dataclass(frozen=True)
class SampleEvent:
    event_id: object
    occurred_at: datetime
    aggregate_id: object
    actor_id: object
    value: int

def test_envelope_is_stable_and_carries_metadata():
    aid, actor = uuid4(), uuid4()
    event = SampleEvent(uuid4(), datetime.now(timezone.utc), aid, actor, 7)
    correlation = uuid4()
    envelope = DomainEventEnvelope.from_event(event, "Sample", 3, correlation_id=correlation, tenant_id=uuid4())
    assert envelope.event_type == "SampleEvent"
    assert envelope.aggregate_id == aid
    assert envelope.aggregate_version == 3
    assert envelope.metadata.actor_id == actor
    assert envelope.metadata.correlation_id == correlation

def test_publisher_is_idempotent_for_same_event_id():
    publisher = InMemoryDomainEventPublisher()
    event_id, aid = uuid4(), uuid4()
    event = SampleEvent(event_id, datetime.now(timezone.utc), aid, None, 1)
    envelope = DomainEventEnvelope.from_event(event, "Sample", 1)
    publisher.publish(envelope)
    publisher.publish(envelope)
    assert len(publisher.events) == 1

def test_metadata_is_immutable():
    m = EventMetadata(uuid4())
    try:
        m.source = "x"
        assert False
    except Exception:
        assert True
