import importlib
import sqlite3
from datetime import datetime, timezone
from uuid import uuid4

from app.modules.white_label.domain.models import WhiteLabelConfiguration
from app.modules.white_label.persistence.sqlite import SQLiteWhiteLabelRepository

apply = importlib.import_module(
    "app.migrations.112_09_001_white_label"
).apply


def make_connection():
    connection = sqlite3.connect(":memory:")
    apply(connection)
    return connection


def test_migration_creates_white_label_table():
    connection = make_connection()

    row = connection.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name = 'white_label_configurations'
        """
    ).fetchone()

    assert row is not None
    assert row[0] == "white_label_configurations"


def test_migration_creates_expected_columns():
    connection = make_connection()

    columns = connection.execute(
        "PRAGMA table_info(white_label_configurations)"
    ).fetchall()

    names = {column[1] for column in columns}

    assert {
        "id",
        "tenant_id",
        "organization_id",
        "display_name",
        "short_name",
        "description",
        "logo_url",
        "favicon_url",
        "primary_color",
        "secondary_color",
        "background_color",
        "theme_color",
        "locale",
        "direction",
        "created_at",
        "updated_at",
        "version",
    } <= names


def test_save_and_get_by_id_round_trip():
    connection = make_connection()
    repository = SQLiteWhiteLabelRepository(connection)

    item = WhiteLabelConfiguration.create(
        tenant_id=uuid4(),
        organization_id=uuid4(),
        display_name="Acme Decisions",
        short_name="ACME",
        description="Acme decision intelligence",
        logo_url="https://example.com/logo.png",
    )

    repository.save(item)

    loaded = repository.get_by_id(item.id)

    assert loaded == item


def test_save_and_get_preserves_custom_branding_values():
    connection = make_connection()
    repository = SQLiteWhiteLabelRepository(connection)

    item = WhiteLabelConfiguration.create(
        tenant_id=uuid4(),
        display_name="Arabic Decisions",
        short_name="AR-DIP",
        description="Arabic white-label tenant",
        primary_color="#AABBCC",
        secondary_color="#DDEEFF",
        background_color="#101010",
        theme_color="#202020",
        locale="ar",
        direction="rtl",
    )

    repository.save(item)

    loaded = repository.get_by_tenant(item.tenant_id)

    assert loaded is not None
    assert loaded.display_name == "Arabic Decisions"
    assert loaded.short_name == "AR-DIP"
    assert loaded.primary_color == "#aabbcc"
    assert loaded.secondary_color == "#ddeeff"
    assert loaded.background_color == "#101010"
    assert loaded.theme_color == "#202020"
    assert loaded.locale == "ar"
    assert loaded.direction == "rtl"


def test_get_by_tenant_returns_only_matching_tenant():
    connection = make_connection()
    repository = SQLiteWhiteLabelRepository(connection)

    first = WhiteLabelConfiguration.create(tenant_id=uuid4())
    second = WhiteLabelConfiguration.create(tenant_id=uuid4())

    repository.save(first)
    repository.save(second)

    assert repository.get_by_tenant(first.tenant_id) == first
    assert repository.get_by_tenant(second.tenant_id) == second
    assert repository.get_by_tenant(uuid4()) is None


def test_same_tenant_cannot_have_two_configurations():
    connection = make_connection()
    repository = SQLiteWhiteLabelRepository(connection)

    tenant_id = uuid4()

    first = WhiteLabelConfiguration.create(tenant_id=tenant_id)
    second = WhiteLabelConfiguration.create(tenant_id=tenant_id)

    repository.save(first)

    try:
        repository.save(second)
    except sqlite3.IntegrityError:
        pass
    else:
        raise AssertionError(
            "duplicate tenant configuration was accepted"
        )


def test_update_preserves_single_tenant_configuration():
    connection = make_connection()
    repository = SQLiteWhiteLabelRepository(connection)

    item = WhiteLabelConfiguration.create(
        tenant_id=uuid4(),
        display_name="Original",
    )

    repository.save(item)

    updated = WhiteLabelConfiguration(
        id=item.id,
        tenant_id=item.tenant_id,
        organization_id=item.organization_id,
        display_name="Updated",
        short_name=item.short_name,
        description=item.description,
        logo_url=item.logo_url,
        favicon_url=item.favicon_url,
        primary_color=item.primary_color,
        secondary_color=item.secondary_color,
        background_color=item.background_color,
        theme_color=item.theme_color,
        locale=item.locale,
        direction=item.direction,
        created_at=item.created_at,
        updated_at=datetime.now(timezone.utc),
        version=item.version + 1,
    )

    repository.save(updated)

    assert repository.get_by_id(item.id) == updated
    assert repository.get_by_tenant(item.tenant_id) == updated


def test_delete_removes_configuration():
    connection = make_connection()
    repository = SQLiteWhiteLabelRepository(connection)

    item = WhiteLabelConfiguration.create(tenant_id=uuid4())

    repository.save(item)
    repository.delete(item.id)

    assert repository.get_by_id(item.id) is None
    assert repository.get_by_tenant(item.tenant_id) is None
