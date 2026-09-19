from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from app.modules.white_label.domain.models import (
    DEFAULT_BACKGROUND_COLOR,
    DEFAULT_DISPLAY_NAME,
    DEFAULT_DIRECTION,
    DEFAULT_LOCALE,
    DEFAULT_PRIMARY_COLOR,
    DEFAULT_SECONDARY_COLOR,
    DEFAULT_SHORT_NAME,
    DEFAULT_THEME_COLOR,
    WhiteLabelConfiguration,
)
from app.modules.white_label.domain.repository import WhiteLabelRepository
from app.shared.domain.errors import InvalidDomainData


def test_create_uses_safe_platform_defaults():
    tenant_id = uuid4()

    item = WhiteLabelConfiguration.create(tenant_id=tenant_id)

    assert item.tenant_id == tenant_id
    assert item.display_name == DEFAULT_DISPLAY_NAME
    assert item.short_name == DEFAULT_SHORT_NAME
    assert item.primary_color == DEFAULT_PRIMARY_COLOR
    assert item.secondary_color == DEFAULT_SECONDARY_COLOR
    assert item.background_color == DEFAULT_BACKGROUND_COLOR
    assert item.theme_color == DEFAULT_THEME_COLOR
    assert item.locale == DEFAULT_LOCALE
    assert item.direction == DEFAULT_DIRECTION
    assert item.version == 1


def test_configuration_is_tenant_scoped():
    tenant_id = uuid4()
    other_tenant_id = uuid4()

    item = WhiteLabelConfiguration.create(
        tenant_id=tenant_id,
        display_name="Tenant One",
    )

    assert item.tenant_id == tenant_id
    assert item.tenant_id != other_tenant_id


def test_organization_is_optional():
    item = WhiteLabelConfiguration.create(tenant_id=uuid4())

    assert item.organization_id is None


def test_organization_id_is_supported():
    organization_id = uuid4()

    item = WhiteLabelConfiguration.create(
        tenant_id=uuid4(),
        organization_id=organization_id,
    )

    assert item.organization_id == organization_id


@pytest.mark.parametrize(
    "field,value",
    [
        ("display_name", ""),
        ("short_name", ""),
        ("description", ""),
    ],
)
def test_required_branding_text_is_rejected(field, value):
    values = {"tenant_id": uuid4(), field: value}

    with pytest.raises(InvalidDomainData):
        WhiteLabelConfiguration.create(**values)


@pytest.mark.parametrize(
    "field,value",
    [
        ("primary_color", "red"),
        ("secondary_color", "#123"),
        ("background_color", "#gggggg"),
        ("theme_color", "123456"),
    ],
)
def test_invalid_colors_are_rejected(field, value):
    values = {"tenant_id": uuid4(), field: value}

    with pytest.raises(InvalidDomainData):
        WhiteLabelConfiguration.create(**values)


@pytest.mark.parametrize(
    "field,value",
    [
        ("logo_url", "logo.png"),
        ("favicon_url", "javascript:alert(1)"),
    ],
)
def test_invalid_brand_urls_are_rejected(field, value):
    values = {"tenant_id": uuid4(), field: value}

    with pytest.raises(InvalidDomainData):
        WhiteLabelConfiguration.create(**values)


def test_valid_brand_urls_are_accepted():
    item = WhiteLabelConfiguration.create(
        tenant_id=uuid4(),
        logo_url="https://example.com/logo.png",
        favicon_url="https://example.com/favicon.ico",
    )

    assert item.logo_url == "https://example.com/logo.png"
    assert item.favicon_url == "https://example.com/favicon.ico"


def test_direction_is_restricted():
    with pytest.raises(InvalidDomainData):
        WhiteLabelConfiguration.create(
            tenant_id=uuid4(),
            direction="auto",
        )


def test_locale_cannot_contain_whitespace():
    with pytest.raises(InvalidDomainData):
        WhiteLabelConfiguration.create(
            tenant_id=uuid4(),
            locale="en US",
        )


def test_version_must_be_positive():
    with pytest.raises(InvalidDomainData):
        WhiteLabelConfiguration(
            tenant_id=uuid4(),
            version=0,
        )


def test_timestamps_must_be_timezone_aware():
    naive = datetime.now()

    with pytest.raises(InvalidDomainData):
        WhiteLabelConfiguration(
            tenant_id=uuid4(),
            created_at=naive,
            updated_at=naive,
        )


def test_updated_at_cannot_precede_created_at():
    now = datetime.now(timezone.utc)

    with pytest.raises(InvalidDomainData):
        WhiteLabelConfiguration(
            tenant_id=uuid4(),
            created_at=now,
            updated_at=now - timedelta(seconds=1),
        )
