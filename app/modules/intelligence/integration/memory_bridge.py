from __future__ import annotations

from dataclasses import asdict, is_dataclass
from enum import Enum
from typing import Any
from uuid import UUID

from app.modules.memory.application.service import MemoryService
from app.modules.memory.domain.models import MemoryType
from app.shared.domain.events import DomainEventEnvelope


def _serialize(value: Any) -> Any:
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return _serialize(asdict(value))
    if isinstance(value, dict):
        return {str(key): _serialize(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_serialize(item) for item in value]
    return value


class DecisionMemoryBridge:
    """
    Converts selected authoritative decision events into durable memory.

    The bridge records context; it never changes decision state.
    """

    _MEMORY_BY_EVENT = {
        "DecisionCreated": MemoryType.DECISION,
        "DecisionApproved": MemoryType.DECISION,
        "DecisionRejected": MemoryType.OBSERVATION,
        "DecisionCancelled": MemoryType.OBSERVATION,
        "DecisionExecuted": MemoryType.DECISION,
        "DecisionClosed": MemoryType.OBSERVATION,
    }

    def __init__(self, memory: MemoryService) -> None:
        self.memory = memory
        self._processed: set[tuple[UUID, UUID]] = set()

    def can_handle(self, event_type: str) -> bool:
        return event_type in self._MEMORY_BY_EVENT

    def handle(self, event: DomainEventEnvelope) -> None:
        if event.aggregate_type != "Decision":
            raise ValueError("event aggregate_type must be Decision")

        if not isinstance(event.aggregate_id, UUID):
            raise ValueError("decision event aggregate_id must be UUID")

        memory_type = self._MEMORY_BY_EVENT.get(event.event_type)
        if memory_type is None:
            return

        tenant_id = event.metadata.tenant_id
        if tenant_id is None:
            return
        if not isinstance(tenant_id, UUID):
            raise ValueError("event tenant_id must be UUID")

        key = (tenant_id, event.event_id)
        if key in self._processed:
            return

        payload = _serialize(event.payload)

        content = (
            f"Decision event {event.event_type}; "
            f"decision_id={event.aggregate_id}; "
            f"aggregate_version={event.aggregate_version}; "
            f"payload={payload}"
        )

        self.memory.remember(
            tenant_id=tenant_id,
            memory_type=memory_type,
            content=content,
            source="decision-domain-event",
            evidence_ids=(),
            confidence=1.0,
        )

        self._processed.add(key)
