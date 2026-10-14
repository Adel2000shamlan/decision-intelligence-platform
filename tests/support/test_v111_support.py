from uuid import uuid4

import pytest

from app.modules.support import (
    SupportPriority,
    SupportService,
    SupportStatus,
)


def test_support_ticket_lifecycle():
    service = SupportService()
    tenant = uuid4()

    ticket = service.create(
        tenant,
        uuid4(),
        "Pilot issue",
        "Unable to complete onboarding",
        SupportPriority.HIGH,
    )
    assert ticket.status == SupportStatus.OPEN

    ticket = service.acknowledge(tenant, ticket.id)
    assert ticket.status == SupportStatus.ACKNOWLEDGED
    assert ticket.acknowledged_at is not None

    ticket = service.resolve(tenant, ticket.id)
    assert ticket.status == SupportStatus.RESOLVED
    assert ticket.resolved_at is not None


def test_support_is_tenant_scoped():
    service = SupportService()
    tenant_a = uuid4()
    tenant_b = uuid4()

    ticket = service.create(
        tenant_a,
        uuid4(),
        "Issue",
        "Details",
    )

    with pytest.raises(PermissionError):
        service.acknowledge(tenant_b, ticket.id)
