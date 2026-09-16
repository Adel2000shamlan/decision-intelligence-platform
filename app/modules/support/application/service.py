from uuid import UUID

from app.modules.support.domain.models import (
    SupportPriority,
    SupportStatus,
    SupportTicket,
)


class SupportService:
    def __init__(self) -> None:
        self._tickets: dict[UUID, SupportTicket] = {}

    def create(
        self,
        tenant_id: UUID,
        reporter_id: UUID,
        title: str,
        description: str,
        priority: SupportPriority = SupportPriority.NORMAL,
    ) -> SupportTicket:
        ticket = SupportTicket.create(
            tenant_id,
            reporter_id,
            title,
            description,
            priority,
        )
        self._tickets[ticket.id] = ticket
        return ticket

    def acknowledge(
        self,
        tenant_id: UUID,
        ticket_id: UUID,
    ) -> SupportTicket:
        ticket = self._get(tenant_id, ticket_id)
        updated = ticket.acknowledge()
        self._tickets[ticket_id] = updated
        return updated

    def resolve(
        self,
        tenant_id: UUID,
        ticket_id: UUID,
    ) -> SupportTicket:
        ticket = self._get(tenant_id, ticket_id)
        updated = ticket.resolve()
        self._tickets[ticket_id] = updated
        return updated

    def tickets(self, tenant_id: UUID) -> tuple[SupportTicket, ...]:
        return tuple(
            ticket
            for ticket in self._tickets.values()
            if ticket.tenant_id == tenant_id
        )

    def _get(self, tenant_id: UUID, ticket_id: UUID) -> SupportTicket:
        ticket = self._tickets.get(ticket_id)
        if ticket is None:
            raise KeyError("support ticket not found")
        if ticket.tenant_id != tenant_id:
            raise PermissionError("support ticket does not belong to tenant")
        return ticket
