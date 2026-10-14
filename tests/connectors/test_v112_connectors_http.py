from uuid import uuid4

import pytest

from app.modules.connectors.domain.models import (
    Connector,
    ConnectorKind,
    ConnectorStatus,
)
from app.modules.connectors.infrastructure.http import GenericHttpConnectorProvider
from app.shared.domain.errors import BusinessRuleViolation


def make_connector(
    *,
    kind=ConnectorKind.GENERIC_HTTP,
    status=ConnectorStatus.ENABLED,
):
    return Connector.create(
        tenant_id=uuid4(),
        name="HTTP",
        kind=kind,
        endpoint="https://example.com/api",
        status=status,
    )


def test_send_delegates_to_transport():
    calls = []

    def transport(endpoint, payload):
        calls.append((endpoint, payload))

    provider = GenericHttpConnectorProvider(transport)
    connector = make_connector()
    payload = {"event": "decision.completed", "value": 42}

    provider.send(connector, payload=payload)

    assert calls == [(connector.endpoint, payload)]


def test_disabled_connector_is_rejected():
    provider = GenericHttpConnectorProvider(lambda endpoint, payload: None)
    connector = make_connector(status=ConnectorStatus.DISABLED)

    with pytest.raises(BusinessRuleViolation, match="connector is disabled"):
        provider.send(connector, payload={"event": "test"})


def test_wrong_connector_kind_is_rejected():
    provider = GenericHttpConnectorProvider(lambda endpoint, payload: None)
    connector = make_connector(kind=ConnectorKind.WEBHOOK)

    with pytest.raises(
        BusinessRuleViolation,
        match="connector kind is not supported",
    ):
        provider.send(connector, payload={"event": "test"})


def test_invalid_payload_is_rejected():
    provider = GenericHttpConnectorProvider(lambda endpoint, payload: None)
    connector = make_connector()

    with pytest.raises(BusinessRuleViolation, match="payload must be a dictionary"):
        provider.send(connector, payload="invalid")


def test_transport_failure_is_not_silently_swallowed():
    def transport(endpoint, payload):
        raise RuntimeError("transport failure")

    provider = GenericHttpConnectorProvider(transport)
    connector = make_connector()

    with pytest.raises(RuntimeError, match="transport failure"):
        provider.send(connector, payload={"event": "test"})
