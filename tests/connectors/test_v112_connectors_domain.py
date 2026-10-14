from uuid import uuid4

import pytest

from app.modules.connectors.domain.models import (
    Connector,
    ConnectorKind,
    ConnectorStatus,
)
from app.shared.domain.errors import BusinessRuleViolation


def test_create_connector():
    tenant_id = uuid4()

    connector = Connector.create(
        tenant_id=tenant_id,
        name="CRM Webhook",
        kind=ConnectorKind.WEBHOOK,
        endpoint="https://example.com/webhook",
    )

    assert connector.tenant_id == tenant_id
    assert connector.name == "CRM Webhook"
    assert connector.kind is ConnectorKind.WEBHOOK
    assert connector.status is ConnectorStatus.ENABLED
    assert connector.endpoint == "https://example.com/webhook"


def test_kind_string_is_coerced():
    connector = Connector.create(
        tenant_id=uuid4(),
        name="HTTP",
        kind="generic_http",
        endpoint="https://example.com",
    )

    assert connector.kind is ConnectorKind.GENERIC_HTTP


def test_status_string_is_coerced():
    connector = Connector.create(
        tenant_id=uuid4(),
        name="HTTP",
        kind=ConnectorKind.GENERIC_HTTP,
        endpoint="https://example.com",
        status="disabled",
    )

    assert connector.status is ConnectorStatus.DISABLED


@pytest.mark.parametrize(
    "kwargs",
    [
        {"tenant_id": "not-a-uuid"},
        {"name": ""},
        {"kind": "invalid"},
        {"endpoint": ""},
        {"status": "invalid"},
    ],
)
def test_invalid_connector_rejected(kwargs):
    base = {
        "tenant_id": uuid4(),
        "name": "Connector",
        "kind": ConnectorKind.GENERIC_HTTP,
        "endpoint": "https://example.com",
    }
    base.update(kwargs)

    with pytest.raises(BusinessRuleViolation):
        Connector.create(**base)


def test_connector_ids_are_unique():
    first = Connector.create(
        tenant_id=uuid4(),
        name="One",
        kind=ConnectorKind.GENERIC_HTTP,
        endpoint="https://one.example.com",
    )
    second = Connector.create(
        tenant_id=first.tenant_id,
        name="Two",
        kind=ConnectorKind.GENERIC_HTTP,
        endpoint="https://two.example.com",
    )

    assert first.id != second.id
