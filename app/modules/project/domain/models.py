from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from uuid import UUID, uuid4

from app.shared.domain.aggregate import AggregateRoot
from app.shared.domain.errors import InvalidDomainData, InvalidStateTransition


class ProjectStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class ProjectCreated:
    event_id: UUID
    occurred_at: datetime
    aggregate_id: UUID
    actor_id: UUID | None
    organization_id: UUID
    name: str


@dataclass(frozen=True)
class ProjectActivated:
    event_id: UUID
    occurred_at: datetime
    aggregate_id: UUID
    actor_id: UUID | None
    previous_status: ProjectStatus


@dataclass(frozen=True)
class ProjectCompleted:
    event_id: UUID
    occurred_at: datetime
    aggregate_id: UUID
    actor_id: UUID | None
    previous_status: ProjectStatus


@dataclass(frozen=True)
class ProjectArchived:
    event_id: UUID
    occurred_at: datetime
    aggregate_id: UUID
    actor_id: UUID | None
    previous_status: ProjectStatus


@dataclass(frozen=True)
class ProjectCancelled:
    event_id: UUID
    occurred_at: datetime
    aggregate_id: UUID
    actor_id: UUID | None
    previous_status: ProjectStatus


@dataclass(frozen=True)
class ProjectRenamed:
    event_id: UUID
    occurred_at: datetime
    aggregate_id: UUID
    actor_id: UUID | None
    old_name: str
    new_name: str


def _required_text(value: str, field_name: str, max_length: int = 200) -> str:
    if not isinstance(value, str):
        raise InvalidDomainData(f"{field_name} must be a string")
    value = value.strip()
    if not value:
        raise InvalidDomainData(f"{field_name} is required")
    if len(value) > max_length:
        raise InvalidDomainData(f"{field_name} exceeds {max_length} characters")
    return value


@dataclass
class Project(AggregateRoot):
    organization_id: UUID
    name: str
    id: UUID = field(default_factory=uuid4)
    status: ProjectStatus = ProjectStatus.DRAFT
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    version: int = 1
    _pending_events: list[object] = field(default_factory=list, init=False, repr=False)

    def __post_init__(self) -> None:
        if not isinstance(self.organization_id, UUID):
            raise InvalidDomainData("organization_id must be UUID")
        self.name = _required_text(self.name, "name")
        if not isinstance(self.status, ProjectStatus):
            try:
                self.status = ProjectStatus(self.status)
            except (ValueError, TypeError) as exc:
                raise InvalidDomainData("invalid project status") from exc
        if not isinstance(self.id, UUID):
            raise InvalidDomainData("id must be UUID")
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
    def create(cls, organization_id: UUID, name: str, actor_id: UUID | None = None) -> "Project":
        project = cls(organization_id=organization_id, name=name)
        project._emit(ProjectCreated(uuid4(), project.updated_at, project.id, actor_id, project.organization_id, project.name))
        return project

    def _touch(self) -> None:
        self.updated_at = datetime.now(timezone.utc)
        self.version += 1

    def _emit(self, event: object) -> None:
        self._pending_events.append(event)

    def pull_events(self) -> tuple[object, ...]:
        events = tuple(self._pending_events)
        self._pending_events.clear()
        return events

    def _transition(self, target: ProjectStatus, actor_id: UUID | None = None) -> None:
        from app.shared.domain.state_machines import PROJECT_STATE_MACHINE
        PROJECT_STATE_MACHINE.transition(self.status, target)
        previous = self.status
        self.status = target
        self._touch()
        event_cls = {
            ProjectStatus.ACTIVE: ProjectActivated,
            ProjectStatus.COMPLETED: ProjectCompleted,
            ProjectStatus.ARCHIVED: ProjectArchived,
            ProjectStatus.CANCELLED: ProjectCancelled,
        }.get(target)
        if event_cls:
            self._emit(event_cls(uuid4(), self.updated_at, self.id, actor_id, previous))

    def activate(self, actor_id: UUID | None = None) -> None:
        self._transition(ProjectStatus.ACTIVE, actor_id)

    def complete(self, actor_id: UUID | None = None) -> None:
        self._transition(ProjectStatus.COMPLETED, actor_id)

    def archive(self, actor_id: UUID | None = None) -> None:
        self._transition(ProjectStatus.ARCHIVED, actor_id)

    def cancel(self, actor_id: UUID | None = None) -> None:
        self._transition(ProjectStatus.CANCELLED, actor_id)

    def transition(self, target: ProjectStatus, actor_id: UUID | None = None) -> None:
        self._transition(target, actor_id)

    def rename(self, new_name: str, actor_id: UUID | None = None) -> None:
        value = _required_text(new_name, "name")
        if value == self.name:
            return
        old = self.name
        self.name = value
        self._touch()
        self._emit(ProjectRenamed(uuid4(), self.updated_at, self.id, actor_id, old, value))
