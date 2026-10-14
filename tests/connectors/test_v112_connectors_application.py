import sqlite3
from uuid import uuid4

import pytest

from app.modules.connectors.application.service import ConnectorService
from app.modules.connectors.domain.models import ConnectorKind, ConnectorStatus
from app.modules.connectors.infrastructure.sqlite import SQLiteConnectorRepository
from app.shared.domain.errors import BusinessRuleViolation


@pytest.fixture
def service():
    connection = sqlite3.connect(":memory:")
    repository = SQLiteConnectorRepository(connection)
    yield ConnectorService(repository)
    connection.close()


def test_register_and_get(service):
    tenant_id = uuid4()

    connector = service.register(
        tenant_id=tenant_id,
        name="CRM",
        kind=ConnectorKind.GENERIC_HTTP,
        endpoint="https://example.com",
    )

    assert service.get(
        tenant_id=tenant_id,
        connector_id=connector.id,
    ) == connector


def test_list_is_tenant_scoped(service):
    tenant_a = uuid4()
    tenant_b = uuid4()

    first = service.register(
        tenant_id=tenant_a,
        name="A",
        kind=ConnectorKind.GENERIC_HTTP,
        endpoint="https://a.example.com",
    )
    second = service.register(
        tenant_id=tenant_b,
        name="B",
        kind=ConnectorKind.GENERIC_HTTP,
        endpoint="https://b.example.com",
    )

    assert service.list(tenant_id=tenant_a) == (first,)
    assert service.list(tenant_id=tenant_b) == (second,)


def test_set_status_updates_connector(service):
    tenant_id = uuid4()

    connector = service.register(
        tenant_id=tenant_id,
        name="CRM",
        kind=ConnectorKind.WEBHOOK,
        endpoint="https://example.com/webhook",
    )

    updated = service.set_status(
        tenant_id=tenant_id,
        connector_id=connector.id,
        status=ConnectorStatus.DISABLED,
    )

    assert updated.status is ConnectorStatus.DISABLED
    assert service.get(
        tenant_id=tenant_id,
        connector_id=connector.id,
    ) == updated


def test_set_status_is_tenant_scoped(service):
    tenant_a = uuid4()
    tenant_b = uuid4()

    connector = service.register(
        tenant_id=tenant_a,
        name="CRM",
        kind=ConnectorKind.GENERIC_HTTP,
        endpoint="https://example.com",
    )

    with pytest.raises(BusinessRuleViolation, match="connector not found"):
        service.set_status(
            tenant_id=tenant_b,
            connector_id=connector.id,
            status=ConnectorStatus.DISABLED,
        )

    assert service.get(
        tenant_id=tenant_a,
        connector_id=connector.id,
    ) == connector


def test_set_status_missing_connector_rejected(service):
    with pytest.raises(BusinessRuleViolation, match="connector not found"):
        service.set_status(
            tenant_id=uuid4(),
            connector_id=uuid4(),
            status=ConnectorStatus.DISABLED,
        )


def test_remove_connector(service):
    tenant_id = uuid4()

    connector = service.register(
        tenant_id=tenant_id,
        name="CRM",
        kind=ConnectorKind.GENERIC_HTTP,
        endpoint="https://example.com",
    )

    service.remove(
        tenant_id=tenant_id,
        connector_id=connector.id,
    )

    assert service.get(
        tenant_id=tenant_id,
        connector_id=connector.id,
    ) is None
