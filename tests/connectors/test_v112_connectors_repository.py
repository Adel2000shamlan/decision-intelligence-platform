import sqlite3
from uuid import uuid4

import pytest

from app.modules.connectors.domain.models import (
    Connector,
    ConnectorKind,
    ConnectorStatus,
)
from app.modules.connectors.infrastructure.sqlite import SQLiteConnectorRepository
from app.shared.domain.errors import BusinessRuleViolation


@pytest.fixture
def repository():
    connection = sqlite3.connect(":memory:")
    repo = SQLiteConnectorRepository(connection)
    yield repo
    connection.close()


def make_connector(
    tenant_id=None,
    name="CRM",
    kind=ConnectorKind.GENERIC_HTTP,
    endpoint="https://example.com",
):
    return Connector.create(
        tenant_id=tenant_id or uuid4(),
        name=name,
        kind=kind,
        endpoint=endpoint,
    )


def test_save_and_get(repository):
    tenant_id = uuid4()
    connector = make_connector(tenant_id=tenant_id)

    repository.save(connector)

    assert repository.get(tenant_id, connector.id) == connector


def test_get_is_tenant_scoped(repository):
    tenant_a = uuid4()
    tenant_b = uuid4()
    connector = make_connector(tenant_id=tenant_a)

    repository.save(connector)

    assert repository.get(tenant_a, connector.id) == connector
    assert repository.get(tenant_b, connector.id) is None


def test_list_is_tenant_scoped_and_ordered(repository):
    tenant_id = uuid4()

    first = make_connector(tenant_id=tenant_id, name="First")
    second = make_connector(tenant_id=tenant_id, name="Second")
    other = make_connector(name="Other")

    repository.save(first)
    repository.save(second)
    repository.save(other)

    assert repository.list(tenant_id) == (first, second)
    assert repository.list(other.tenant_id) == (other,)


def test_upsert(repository):
    tenant_id = uuid4()
    connector = make_connector(tenant_id=tenant_id)

    repository.save(connector)

    updated = Connector(
        id=connector.id,
        tenant_id=tenant_id,
        name=connector.name,
        kind=connector.kind,
        status=ConnectorStatus.DISABLED,
        endpoint="https://updated.example.com",
        created_at=connector.created_at,
    )

    repository.save(updated)

    assert repository.get(tenant_id, connector.id) == updated


def test_duplicate_name_is_rejected_within_tenant(repository):
    tenant_id = uuid4()

    first = make_connector(tenant_id=tenant_id, name="Same")
    second = make_connector(tenant_id=tenant_id, name="Same")

    repository.save(first)

    with pytest.raises(BusinessRuleViolation):
        repository.save(second)


def test_same_name_allowed_for_different_tenants(repository):
    tenant_a = uuid4()
    tenant_b = uuid4()

    first = make_connector(tenant_id=tenant_a, name="Same")
    second = make_connector(tenant_id=tenant_b, name="Same")

    repository.save(first)
    repository.save(second)

    assert repository.get(tenant_a, first.id) == first
    assert repository.get(tenant_b, second.id) == second


def test_delete_is_tenant_scoped(repository):
    tenant_a = uuid4()
    tenant_b = uuid4()
    connector = make_connector(tenant_id=tenant_a)

    repository.save(connector)

    repository.delete(tenant_b, connector.id)
    assert repository.get(tenant_a, connector.id) == connector

    repository.delete(tenant_a, connector.id)
    assert repository.get(tenant_a, connector.id) is None
