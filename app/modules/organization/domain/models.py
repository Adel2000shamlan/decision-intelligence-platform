from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from uuid import UUID, uuid4

from app.shared.domain.aggregate import AggregateRoot
from app.shared.domain.errors import InvalidDomainData, InvalidStateTransition


class OrganizationStatus(str, Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    ARCHIVED = "archived"


@dataclass(frozen=True)
class DomainEvent:
    event_id: UUID
    occurred_at: datetime
    aggregate_id: UUID
    actor_id: UUID | None = None


@dataclass(frozen=True)
class OrganizationCreated(DomainEvent):
    name: str = ""
    slug: str = ""


@dataclass(frozen=True)
class OrganizationSuspended(DomainEvent):
    previous_status: OrganizationStatus = OrganizationStatus.ACTIVE


@dataclass(frozen=True)
class OrganizationReactivated(DomainEvent):
    previous_status: OrganizationStatus = OrganizationStatus.SUSPENDED


@dataclass(frozen=True)
class OrganizationArchived(DomainEvent):
    previous_status: OrganizationStatus = OrganizationStatus.ACTIVE


@dataclass(frozen=True)
class OrganizationRenamed(DomainEvent):
    old_name: str = ""
    new_name: str = ""


@dataclass(frozen=True)
class OrganizationSlugChanged(DomainEvent):
    old_slug: str = ""
    new_slug: str = ""


def _clean_required(value: str, field_name: str) -> str:
    if not isinstance(value, str):
        raise InvalidDomainData(f"{field_name} must be a string")
    value = value.strip()
    if not value:
        raise InvalidDomainData(f"{field_name} is required")
    return value


def validate_slug(slug: str) -> str:
    value = _clean_required(slug, "slug")
    if len(value) > 100:
        raise InvalidDomainData("slug exceeds 100 characters")
    if any(ch.isspace() for ch in value):
        raise InvalidDomainData("slug must not contain whitespace")
    if not all(ch.isalnum() or ch in "-_" for ch in value):
        raise InvalidDomainData("slug contains invalid characters")
    return value.lower()


@dataclass
class Organization(AggregateRoot):
    name: str
    slug: str
    id: UUID = field(default_factory=uuid4)
    status: OrganizationStatus = OrganizationStatus.ACTIVE
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    version: int = 1
    _pending_events: list[DomainEvent] = field(default_factory=list, init=False, repr=False)

    def __post_init__(self) -> None:
        self.name = _clean_required(self.name, "name")
        self.slug = validate_slug(self.slug)
        if not isinstance(self.status, OrganizationStatus):
            try:
                self.status = OrganizationStatus(self.status)
            except (ValueError, TypeError) as exc:
                raise InvalidDomainData("invalid organization status") from exc
        if self.version < 1:
            raise InvalidDomainData("version must be >= 1")

    def validate_invariants(self) -> None:
        super().validate_invariants()
        from app.shared.domain.validation import DomainValidator
        DomainValidator.validate_timestamp(self.created_at, "created_at")
        DomainValidator.validate_timestamp(self.updated_at, "updated_at")
        if self.updated_at < self.created_at:
            raise InvalidDomainData("updated_at cannot precede created_at")
        from .rules import RULES
        RULES.assert_valid(self)

    @classmethod
    def create(cls, name: str, slug: str, actor_id: UUID | None = None) -> "Organization":
        organization = cls(name=name, slug=slug)
        organization._emit(OrganizationCreated(
            event_id=uuid4(), occurred_at=organization.updated_at,
            aggregate_id=organization.id, actor_id=actor_id,
            name=organization.name, slug=organization.slug,
        ))
        return organization

    def _touch(self) -> None:
        self.updated_at = datetime.now(timezone.utc)
        self.version += 1

    def _emit(self, event: DomainEvent) -> None:
        self._pending_events.append(event)

    def pull_events(self) -> tuple[DomainEvent, ...]:
        events = tuple(self._pending_events)
        self._pending_events.clear()
        return events

    def suspend(self, actor_id: UUID | None = None) -> None:
        from app.shared.domain.state_machines import ORGANIZATION_STATE_MACHINE
        ORGANIZATION_STATE_MACHINE.transition(self.status, OrganizationStatus.SUSPENDED)
        previous = self.status
        self.status = OrganizationStatus.SUSPENDED
        self._touch()
        self._emit(OrganizationSuspended(uuid4(), self.updated_at, self.id, actor_id, previous))

    def reactivate(self, actor_id: UUID | None = None) -> None:
        from app.shared.domain.state_machines import ORGANIZATION_STATE_MACHINE
        ORGANIZATION_STATE_MACHINE.transition(self.status, OrganizationStatus.ACTIVE)
        previous = self.status
        self.status = OrganizationStatus.ACTIVE
        self._touch()
        self._emit(OrganizationReactivated(uuid4(), self.updated_at, self.id, actor_id, previous))

    def archive(self, actor_id: UUID | None = None) -> None:
        from app.shared.domain.state_machines import ORGANIZATION_STATE_MACHINE
        ORGANIZATION_STATE_MACHINE.transition(self.status, OrganizationStatus.ARCHIVED)
        previous = self.status
        self.status = OrganizationStatus.ARCHIVED
        self._touch()
        self._emit(OrganizationArchived(uuid4(), self.updated_at, self.id, actor_id, previous))

    def rename(self, new_name: str, actor_id: UUID | None = None) -> None:
        value = _clean_required(new_name, "name")
        if value == self.name:
            return
        old = self.name
        self.name = value
        self._touch()
        self._emit(OrganizationRenamed(uuid4(), self.updated_at, self.id, actor_id, old, value))

    def change_slug(self, new_slug: str, actor_id: UUID | None = None) -> None:
        value = validate_slug(new_slug)
        if value == self.slug:
            return
        old = self.slug
        self.slug = value
        self._touch()
        self._emit(OrganizationSlugChanged(uuid4(), self.updated_at, self.id, actor_id, old, value))
