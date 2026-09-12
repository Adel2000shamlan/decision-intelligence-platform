from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Protocol
from uuid import UUID, uuid4


class DomainEvent(Protocol):
    event_id: UUID
    occurred_at: datetime
    aggregate_id: UUID
    actor_id: UUID | None


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True, slots=True)
class EventMetadata:
    correlation_id: UUID
    causation_id: UUID | None = None
    actor_id: UUID | None = None
    tenant_id: UUID | None = None
    source: str = "domain"


@dataclass(frozen=True, slots=True)
class DomainEventEnvelope:
    """Stable transport-neutral envelope around a domain event."""
    event_id: UUID
    event_type: str
    occurred_at: datetime
    aggregate_id: UUID
    aggregate_type: str
    aggregate_version: int
    payload: Any
    metadata: EventMetadata

    @classmethod
    def from_event(cls, event: DomainEvent, aggregate_type: str, aggregate_version: int,
                   *, correlation_id: UUID | None = None, causation_id: UUID | None = None,
                   tenant_id: UUID | None = None) -> "DomainEventEnvelope":
        return cls(
            event_id=event.event_id,
            event_type=type(event).__name__,
            occurred_at=event.occurred_at,
            aggregate_id=event.aggregate_id,
            aggregate_type=aggregate_type,
            aggregate_version=aggregate_version,
            payload=event,
            metadata=EventMetadata(
                correlation_id=correlation_id or uuid4(),
                causation_id=causation_id,
                actor_id=event.actor_id,
                tenant_id=tenant_id,
            ),
        )


class DomainEventPublisher(Protocol):
    def publish(self, event: DomainEventEnvelope) -> None: ...


class InMemoryDomainEventPublisher:
    """Deterministic test adapter; production transport is deliberately external."""
    def __init__(self) -> None:
        self.events: list[DomainEventEnvelope] = []

    def publish(self, event: DomainEventEnvelope) -> None:
        if any(existing.event_id == event.event_id for existing in self.events):
            return
        self.events.append(event)
