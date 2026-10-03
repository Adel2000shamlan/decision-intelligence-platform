from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from enum import Enum
from typing import Any
from uuid import UUID

from app.infrastructure.events import EventBus, EventStore, StoredEvent
from app.shared.domain.events import DomainEventEnvelope, DomainEventPublisher


def _serialize(value: Any) -> Any:
    """Convert domain event payloads into transport-safe values."""
    if isinstance(value, UUID):
        return str(value)

    if isinstance(value, (datetime, date)):
        return value.isoformat()

    if isinstance(value, Enum):
        return value.value

    if is_dataclass(value):
        return _serialize(asdict(value))

    if isinstance(value, dict):
        return {str(key): _serialize(item) for key, item in value.items()}

    if isinstance(value, (list, tuple)):
        return [_serialize(item) for item in value]

    if value is None or isinstance(value, (str, int, float, bool)):
        return value

    return str(value)


class EventBusDomainEventPublisher(DomainEventPublisher):
    """Adapter from the shared domain-event contract to the infrastructure EventBus.

    The adapter keeps domain events transport-neutral while allowing the existing
    infrastructure EventBus/EventStore to consume a stable envelope.
    """

    def __init__(
        self,
        event_bus: EventBus | None = None,
        event_store: EventStore | None = None,
    ) -> None:
        self.event_bus = event_bus or EventBus()
        self.event_store = event_store

    def publish(self, event: DomainEventEnvelope) -> None:
        stored = StoredEvent(
            event_id=str(event.event_id),
            event_type=event.event_type,
            aggregate_id=str(event.aggregate_id),
            payload={
                "payload": _serialize(event.payload),
                "metadata": {
                    "correlation_id": str(event.metadata.correlation_id),
                    "causation_id": (
                        str(event.metadata.causation_id)
                        if event.metadata.causation_id is not None
                        else None
                    ),
                    "actor_id": (
                        str(event.metadata.actor_id)
                        if event.metadata.actor_id is not None
                        else None
                    ),
                    "tenant_id": (
                        str(event.metadata.tenant_id)
                        if event.metadata.tenant_id is not None
                        else None
                    ),
                    "source": event.metadata.source,
                },
                "aggregate_type": event.aggregate_type,
                "aggregate_version": event.aggregate_version,
            },
            occurred_at=event.occurred_at,
            correlation_id=str(event.metadata.correlation_id),
        )

        if self.event_store is not None:
            if not self.event_store.append(stored):
                return

        self.event_bus.publish(stored)


def envelope_from_event(
    event: Any,
    aggregate_type: str,
    aggregate_version: int,
    *,
    correlation_id: UUID | None = None,
    causation_id: UUID | None = None,
    tenant_id: UUID | None = None,
) -> DomainEventEnvelope:
    """Create the shared envelope without coupling callers to its constructor."""
    return DomainEventEnvelope.from_event(
        event,
        aggregate_type,
        aggregate_version,
        correlation_id=correlation_id,
        causation_id=causation_id,
        tenant_id=tenant_id,
    )
