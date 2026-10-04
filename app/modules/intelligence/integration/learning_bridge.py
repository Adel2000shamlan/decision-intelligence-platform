from __future__ import annotations

from uuid import UUID

from app.modules.learning.application import LearningService
from app.modules.learning.domain.models import LearningOutcomeType
from app.shared.domain.events import DomainEventEnvelope


class DecisionLearningBridge:
    """
    Converts authoritative decision lifecycle events into observed learning data.

    This bridge is intentionally one-way:
        Decision lifecycle -> Learning observation

    It never approves, rejects, executes, or otherwise changes the decision.
    """

    _OUTCOME_BY_EVENT = {
        "DecisionExecuted": LearningOutcomeType.SUCCESS,
        "DecisionRejected": LearningOutcomeType.FAILURE,
        "DecisionCancelled": LearningOutcomeType.UNKNOWN,
        "DecisionClosed": LearningOutcomeType.SUCCESS,
    }

    def __init__(self, learning: LearningService) -> None:
        self.learning = learning
        self._processed: set[tuple[UUID, UUID]] = set()

    def can_handle(self, event_type: str) -> bool:
        return event_type in self._OUTCOME_BY_EVENT

    def handle(
        self,
        event: DomainEventEnvelope,
        *,
        tenant_id: UUID | None = None,
    ) -> None:
        if event.aggregate_type != "Decision":
            raise ValueError("event aggregate_type must be Decision")

        if not isinstance(event.aggregate_id, UUID):
            raise ValueError("decision event aggregate_id must be UUID")

        if event.event_type not in self._OUTCOME_BY_EVENT:
            return

        event_tenant = event.metadata.tenant_id

        if event_tenant is not None and not isinstance(event_tenant, UUID):
            raise ValueError("event metadata tenant_id must be UUID")

        if tenant_id is not None and not isinstance(tenant_id, UUID):
            raise ValueError("tenant_id must be UUID")

        if event_tenant is not None and tenant_id is not None and event_tenant != tenant_id:
            raise ValueError("tenant_id does not match event metadata tenant_id")

        effective_tenant = event_tenant or tenant_id
        if effective_tenant is None:
            return

        key = (effective_tenant, event.event_id)
        if key in self._processed:
            return

        outcome_type = self._OUTCOME_BY_EVENT[event.event_type]

        self.learning.observe(
            tenant_id=effective_tenant,
            decision_id=event.aggregate_id,
            outcome_type=outcome_type,
            metric="decision.lifecycle.outcome",
            source="decision-domain-event",
            notes=f"Observed from {event.event_type}",
            observed_at=event.occurred_at,
            confidence=1.0,
        )

        self._processed.add(key)
