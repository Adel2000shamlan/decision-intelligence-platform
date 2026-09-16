from uuid import uuid4
import sqlite3

import pytest

from app.modules.connectors.application.registry import ConnectorProviderRegistry
from app.modules.connectors.application.service import ConnectorService
from app.modules.connectors.domain.models import ConnectorKind
from app.modules.connectors.infrastructure.sqlite import SQLiteConnectorRepository
from app.shared.domain.errors import BusinessRuleViolation


class FakeProvider:
    def __init__(self):
        self.calls = []

    def send(self, connector, *, payload):
        self.calls.append((connector, payload))


def make_service():
    repository = SQLiteConnectorRepository(sqlite3.connect(":memory:"))
    registry = ConnectorProviderRegistry()
    provider = FakeProvider()
    registry.register(ConnectorKind.GENERIC_HTTP, provider)
    service = ConnectorService(repository, registry)
    return service, provider


def test_send_routes_to_registered_provider():
    service, provider = make_service()
    tenant_id = uuid4()

    connector = service.register(
        tenant_id=tenant_id,
        name="events",
        kind=ConnectorKind.GENERIC_HTTP,
        endpoint="https://example.com/events",
    )

    payload = {"event": "decision.completed", "decision_id": "123"}

    service.send(
        tenant_id=tenant_id,
        connector_id=connector.id,
        payload=payload,
    )

    assert len(provider.calls) == 1
    sent_connector, sent_payload = provider.calls[0]
    assert sent_connector.id == connector.id
    assert sent_payload == payload


def test_send_is_tenant_scoped():
    service, provider = make_service()
    owner_tenant = uuid4()
    other_tenant = uuid4()

    connector = service.register(
        tenant_id=owner_tenant,
        name="events",
        kind=ConnectorKind.GENERIC_HTTP,
        endpoint="https://example.com/events",
    )

    with pytest.raises(BusinessRuleViolation, match="connector not found"):
        service.send(
            tenant_id=other_tenant,
            connector_id=connector.id,
            payload={"event": "test"},
        )

    assert provider.calls == []


def test_send_without_registry_is_rejected():
    repository = SQLiteConnectorRepository(sqlite3.connect(":memory:"))
    service = ConnectorService(repository)
    tenant_id = uuid4()

    connector = service.register(
        tenant_id=tenant_id,
        name="events",
        kind=ConnectorKind.GENERIC_HTTP,
        endpoint="https://example.com/events",
    )

    with pytest.raises(
        BusinessRuleViolation,
        match="registry is not configured",
    ):
        service.send(
            tenant_id=tenant_id,
            connector_id=connector.id,
            payload={"event": "test"},
        )


def test_send_missing_connector_is_rejected():
    service, provider = make_service()

    with pytest.raises(BusinessRuleViolation, match="connector not found"):
        service.send(
            tenant_id=uuid4(),
            connector_id=uuid4(),
            payload={"event": "test"},
        )

    assert provider.calls == []
