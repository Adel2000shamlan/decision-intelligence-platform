from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4
from urllib.parse import urlparse

from app.shared.domain.errors import InvalidDomainData


DEFAULT_DISPLAY_NAME = "Decision Intelligence Platform"
DEFAULT_SHORT_NAME = "DIP"
DEFAULT_DESCRIPTION = "Decision Intelligence Platform"
DEFAULT_PRIMARY_COLOR = "#0f172a"
DEFAULT_SECONDARY_COLOR = "#334155"
DEFAULT_BACKGROUND_COLOR = "#ffffff"
DEFAULT_THEME_COLOR = "#0f172a"
DEFAULT_LOCALE = "en"
DEFAULT_DIRECTION = "ltr"


def _required_text(value: str, field_name: str, max_length: int) -> str:
    if not isinstance(value, str):
        raise InvalidDomainData(f"{field_name} must be a string")
    value = value.strip()
    if not value:
        raise InvalidDomainData(f"{field_name} is required")
    if len(value) > max_length:
        raise InvalidDomainData(
            f"{field_name} exceeds {max_length} characters"
        )
    return value


def _optional_text(
    value: str | None,
    field_name: str,
    max_length: int,
) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise InvalidDomainData(f"{field_name} must be a string")
    value = value.strip()
    if not value:
        return None
    if len(value) > max_length:
        raise InvalidDomainData(
            f"{field_name} exceeds {max_length} characters"
        )
    return value


def _validate_uuid(value: UUID, field_name: str) -> UUID:
    if not isinstance(value, UUID):
        raise InvalidDomainData(f"{field_name} must be a UUID")
    return value


def _validate_url(value: str | None, field_name: str) -> str | None:
    value = _optional_text(value, field_name, 2048)
    if value is None:
        return None

    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise InvalidDomainData(
            f"{field_name} must be an absolute HTTP(S) URL"
        )
    return value


def _validate_color(value: str, field_name: str) -> str:
    value = _required_text(value, field_name, 7)
    if len(value) != 7 or value[0] != "#":
        raise InvalidDomainData(
            f"{field_name} must be a 7-character hexadecimal color"
        )

    try:
        int(value[1:], 16)
    except ValueError as exc:
        raise InvalidDomainData(
            f"{field_name} must be a 7-character hexadecimal color"
        ) from exc

    return value.lower()


def _validate_locale(value: str) -> str:
    value = _required_text(value, "locale", 20)
    if any(ch.isspace() for ch in value):
        raise InvalidDomainData("locale must not contain whitespace")
    return value


def _validate_direction(value: str) -> str:
    value = _required_text(value, "direction", 3).lower()
    if value not in {"ltr", "rtl"}:
        raise InvalidDomainData("direction must be either 'ltr' or 'rtl'")
    return value


@dataclass(frozen=True)
class WhiteLabelConfiguration:
    tenant_id: UUID
    organization_id: UUID | None = None
    display_name: str = DEFAULT_DISPLAY_NAME
    short_name: str = DEFAULT_SHORT_NAME
    description: str = DEFAULT_DESCRIPTION
    logo_url: str | None = None
    favicon_url: str | None = None
    primary_color: str = DEFAULT_PRIMARY_COLOR
    secondary_color: str = DEFAULT_SECONDARY_COLOR
    background_color: str = DEFAULT_BACKGROUND_COLOR
    theme_color: str = DEFAULT_THEME_COLOR
    locale: str = DEFAULT_LOCALE
    direction: str = DEFAULT_DIRECTION
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    updated_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    version: int = 1

    def __post_init__(self) -> None:
        _validate_uuid(self.tenant_id, "tenant_id")

        if self.organization_id is not None:
            _validate_uuid(self.organization_id, "organization_id")

        _validate_uuid(self.id, "id")

        object.__setattr__(
            self,
            "display_name",
            _required_text(self.display_name, "display_name", 200),
        )
        object.__setattr__(
            self,
            "short_name",
            _required_text(self.short_name, "short_name", 50),
        )
        object.__setattr__(
            self,
            "description",
            _required_text(self.description, "description", 500),
        )

        object.__setattr__(
            self,
            "logo_url",
            _validate_url(self.logo_url, "logo_url"),
        )
        object.__setattr__(
            self,
            "favicon_url",
            _validate_url(self.favicon_url, "favicon_url"),
        )

        object.__setattr__(
            self,
            "primary_color",
            _validate_color(self.primary_color, "primary_color"),
        )
        object.__setattr__(
            self,
            "secondary_color",
            _validate_color(
                self.secondary_color,
                "secondary_color",
            ),
        )
        object.__setattr__(
            self,
            "background_color",
            _validate_color(
                self.background_color,
                "background_color",
            ),
        )
        object.__setattr__(
            self,
            "theme_color",
            _validate_color(self.theme_color, "theme_color"),
        )

        object.__setattr__(
            self,
            "locale",
            _validate_locale(self.locale),
        )
        object.__setattr__(
            self,
            "direction",
            _validate_direction(self.direction),
        )

        if self.version < 1:
            raise InvalidDomainData("version must be >= 1")

        if not isinstance(self.created_at, datetime):
            raise InvalidDomainData("created_at must be a datetime")

        if not isinstance(self.updated_at, datetime):
            raise InvalidDomainData("updated_at must be a datetime")

        if self.created_at.tzinfo is None:
            raise InvalidDomainData("created_at must be timezone-aware")

        if self.updated_at.tzinfo is None:
            raise InvalidDomainData("updated_at must be timezone-aware")

        if self.updated_at < self.created_at:
            raise InvalidDomainData(
                "updated_at cannot precede created_at"
            )

    @classmethod
    def create(
        cls,
        *,
        tenant_id: UUID,
        organization_id: UUID | None = None,
        display_name: str = DEFAULT_DISPLAY_NAME,
        short_name: str = DEFAULT_SHORT_NAME,
        description: str = DEFAULT_DESCRIPTION,
        logo_url: str | None = None,
        favicon_url: str | None = None,
        primary_color: str = DEFAULT_PRIMARY_COLOR,
        secondary_color: str = DEFAULT_SECONDARY_COLOR,
        background_color: str = DEFAULT_BACKGROUND_COLOR,
        theme_color: str = DEFAULT_THEME_COLOR,
        locale: str = DEFAULT_LOCALE,
        direction: str = DEFAULT_DIRECTION,
    ) -> "WhiteLabelConfiguration":
        return cls(
            tenant_id=tenant_id,
            organization_id=organization_id,
            display_name=display_name,
            short_name=short_name,
            description=description,
            logo_url=logo_url,
            favicon_url=favicon_url,
            primary_color=primary_color,
            secondary_color=secondary_color,
            background_color=background_color,
            theme_color=theme_color,
            locale=locale,
            direction=direction,
        )
