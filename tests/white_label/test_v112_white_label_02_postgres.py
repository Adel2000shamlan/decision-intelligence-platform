import os
from datetime import datetime, timezone
from uuid import uuid4

import psycopg
import pytest

from app.modules.white_label.domain.models import (
    WhiteLabelConfiguration,
)
from app.modules.white_label.persistence.postgres import (
    PostgreSQLWhiteLabelRepository,
)


DATABASE_URL = os.getenv("DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not DATABASE_URL,
    reason="DATABASE_URL is not configured",
)


@pytest.fixture
def repository():
    with psycopg.connect(DATABASE_URL) as connection:
        repo = PostgreSQLWhiteLabelRepository(connection)
        tenant_id = uuid4()

        try:
            yield repo, connection, tenant_id
        finally:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    DELETE FROM white_label_configurations
                    WHERE tenant_id = %s
                    """,
                    (tenant_id,),
                )
            connection.commit()


def make_configuration(
    tenant_id,
    *,
    organization_id=None,
    display_name="Postgres White Label",
):
    now = datetime.now(timezone.utc)

    return WhiteLabelConfiguration(
        tenant_id=tenant_id,
        organization_id=organization_id,
        display_name=display_name,
        short_name="PWL",
        description="PostgreSQL white-label test",
        logo_url="https://example.com/logo.png",
        favicon_url="https://example.com/favicon.ico",
        primary_color="#112233",
        secondary_color="#445566",
        background_color="#ffffff",
        theme_color="#112233",
        locale="en",
        direction="ltr",
        created_at=now,
        updated_at=now,
        version=1,
    )


def test_postgres_white_label_crud(repository):
    repo, _, tenant_id = repository
    configuration = make_configuration(tenant_id)

    assert repo.save(configuration) == configuration
    assert repo.get_by_id(configuration.id) == configuration
    assert repo.get_by_tenant(tenant_id) == configuration

    repo.delete(configuration.id)

    assert repo.get_by_id(configuration.id) is None
    assert repo.get_by_tenant(tenant_id) is None


def test_postgres_white_label_tenant_isolation(repository):
    repo, _, tenant_id = repository
    other_tenant = uuid4()

    configuration = make_configuration(tenant_id)
    repo.save(configuration)

    assert repo.get_by_tenant(other_tenant) is None


def test_postgres_white_label_update(repository):
    repo, _, tenant_id = repository
    configuration = make_configuration(tenant_id)
    repo.save(configuration)

    updated = WhiteLabelConfiguration(
        tenant_id=tenant_id,
        organization_id=configuration.organization_id,
        display_name="Updated White Label",
        short_name=configuration.short_name,
        description=configuration.description,
        logo_url=configuration.logo_url,
        favicon_url=configuration.favicon_url,
        primary_color=configuration.primary_color,
        secondary_color=configuration.secondary_color,
        background_color=configuration.background_color,
        theme_color=configuration.theme_color,
        locale=configuration.locale,
        direction=configuration.direction,
        id=configuration.id,
        created_at=configuration.created_at,
        updated_at=datetime.now(timezone.utc),
        version=2,
    )

    assert repo.save(updated) == updated
    assert repo.get_by_id(configuration.id) == updated
    assert repo.get_by_tenant(tenant_id) == updated


def test_postgres_white_label_duplicate_tenant_is_rejected(repository):
    repo, _, tenant_id = repository

    first = make_configuration(tenant_id)
    second = make_configuration(
        tenant_id,
        display_name="Second White Label",
    )

    repo.save(first)

    with pytest.raises(Exception):
        repo.save(second)


def test_postgres_white_label_cross_tenant_update_is_rejected(repository):
    repo, _, tenant_id = repository
    other_tenant = uuid4()

    configuration = make_configuration(tenant_id)
    repo.save(configuration)

    foreign_configuration = WhiteLabelConfiguration(
        tenant_id=other_tenant,
        organization_id=configuration.organization_id,
        display_name="Foreign Tenant",
        short_name=configuration.short_name,
        description=configuration.description,
        logo_url=configuration.logo_url,
        favicon_url=configuration.favicon_url,
        primary_color=configuration.primary_color,
        secondary_color=configuration.secondary_color,
        background_color=configuration.background_color,
        theme_color=configuration.theme_color,
        locale=configuration.locale,
        direction=configuration.direction,
        id=configuration.id,
        created_at=configuration.created_at,
        updated_at=datetime.now(timezone.utc),
        version=2,
    )

    with pytest.raises(Exception):
        repo.save(foreign_configuration)

    assert repo.get_by_tenant(tenant_id) == configuration
    assert repo.get_by_tenant(other_tenant) is None
