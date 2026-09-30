from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4

from app.shared.domain.aggregate import AggregateRoot
from app.shared.domain.errors import InvalidDomainData
from app.shared.domain.validation import DomainValidator

from .state_machine import BUSINESS_ASSESSMENT_STATE_MACHINE, BusinessAssessmentStatus


def _required_text(value: str, field_name: str, max_length: int) -> str:
    if not isinstance(value, str):
        raise InvalidDomainData(f"{field_name} must be a string")
    value = value.strip()
    if not value:
        raise InvalidDomainData(f"{field_name} is required")
    if len(value) > max_length:
        raise InvalidDomainData(f"{field_name} exceeds {max_length} characters")
    return value


@dataclass(frozen=True)
class BusinessAssessmentCreated:
    event_id: UUID
    occurred_at: datetime
    aggregate_id: UUID
    actor_id: UUID | None
    organization_id: UUID
    title: str


@dataclass(frozen=True)
class BusinessAssessmentDataCollectionStarted:
    event_id: UUID
    occurred_at: datetime
    aggregate_id: UUID
    actor_id: UUID | None
    previous_status: BusinessAssessmentStatus


@dataclass(frozen=True)
class BusinessAssessmentAnalysisStarted:
    event_id: UUID
    occurred_at: datetime
    aggregate_id: UUID
    actor_id: UUID | None
    previous_status: BusinessAssessmentStatus


@dataclass(frozen=True)
class BusinessAssessmentCompleted:
    event_id: UUID
    occurred_at: datetime
    aggregate_id: UUID
    actor_id: UUID | None
    previous_status: BusinessAssessmentStatus


@dataclass(frozen=True)
class BusinessAssessmentArchived:
    event_id: UUID
    occurred_at: datetime
    aggregate_id: UUID
    actor_id: UUID | None
    previous_status: BusinessAssessmentStatus


@dataclass(frozen=True)
class BusinessAssessmentUpdated:
    event_id: UUID
    occurred_at: datetime
    aggregate_id: UUID
    actor_id: UUID | None
    old_title: str
    new_title: str


@dataclass
class BusinessAssessment(AggregateRoot):
    organization_id: UUID
    title: str
    idea_description: str = ""
    id: UUID = field(default_factory=uuid4)
    status: BusinessAssessmentStatus = BusinessAssessmentStatus.DRAFT
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    version: int = 1
    _pending_events: list[object] = field(default_factory=list, init=False, repr=False)

    def __post_init__(self) -> None:
        DomainValidator.validate_uuid(self.organization_id, "organization_id")
        self.title = _required_text(self.title, "title", 200)
        if not isinstance(self.idea_description, str):
            raise InvalidDomainData("idea_description must be a string")
        self.idea_description = self.idea_description.strip()
        if len(self.idea_description) > 4000:
            raise InvalidDomainData("idea_description exceeds 4000 characters")
        if not isinstance(self.status, BusinessAssessmentStatus):
            try:
                self.status = BusinessAssessmentStatus(self.status)
            except (ValueError, TypeError) as exc:
                raise InvalidDomainData("invalid business assessment status") from exc
        DomainValidator.validate_uuid(self.id, "id")
        DomainValidator.validate_version(self.version)

    def validate_invariants(self) -> None:
        super().validate_invariants()
        DomainValidator.validate_uuid(self.organization_id, "organization_id")
        DomainValidator.validate_timestamp(self.created_at, "created_at")
        DomainValidator.validate_timestamp(self.updated_at, "updated_at")
        if self.updated_at < self.created_at:
            raise InvalidDomainData("updated_at cannot precede created_at")
        DomainValidator.validate_string(self.title, "title", 200)
        if len(self.idea_description) > 4000:
            raise InvalidDomainData("idea_description exceeds 4000 characters")
        DomainValidator.validate_event_sequence(self._pending_events, self.id)

    @classmethod
    def create(cls, organization_id: UUID, title: str, idea_description: str = "", actor_id: UUID | None = None) -> "BusinessAssessment":
        assessment = cls(
            organization_id=organization_id,
            title=title,
            idea_description=idea_description,
        )
        assessment._emit(BusinessAssessmentCreated(
            uuid4(), assessment.updated_at, assessment.id, actor_id,
            assessment.organization_id, assessment.title,
        ))
        return assessment

    def _touch(self) -> None:
        self.updated_at = datetime.now(timezone.utc)
        self.version += 1

    def _emit(self, event: object) -> None:
        self._pending_events.append(event)

    def pull_events(self) -> tuple[object, ...]:
        events = tuple(self._pending_events)
        self._pending_events.clear()
        return events

    def _transition(self, target: BusinessAssessmentStatus, actor_id: UUID | None = None) -> None:
        BUSINESS_ASSESSMENT_STATE_MACHINE.transition(self.status, target)
        previous = self.status
        self.status = target
        self._touch()
        event_cls = {
            BusinessAssessmentStatus.DATA_COLLECTION: BusinessAssessmentDataCollectionStarted,
            BusinessAssessmentStatus.UNDER_ANALYSIS: BusinessAssessmentAnalysisStarted,
            BusinessAssessmentStatus.COMPLETED: BusinessAssessmentCompleted,
            BusinessAssessmentStatus.ARCHIVED: BusinessAssessmentArchived,
        }.get(target)
        if event_cls is not None:
            self._emit(event_cls(uuid4(), self.updated_at, self.id, actor_id, previous))

    def start_data_collection(self, actor_id: UUID | None = None) -> None:
        self._transition(BusinessAssessmentStatus.DATA_COLLECTION, actor_id)

    def start_analysis(self, actor_id: UUID | None = None) -> None:
        self._transition(BusinessAssessmentStatus.UNDER_ANALYSIS, actor_id)

    def complete(self, actor_id: UUID | None = None) -> None:
        self._transition(BusinessAssessmentStatus.COMPLETED, actor_id)

    def archive(self, actor_id: UUID | None = None) -> None:
        self._transition(BusinessAssessmentStatus.ARCHIVED, actor_id)

    def return_to_data_collection(self, actor_id: UUID | None = None) -> None:
        self._transition(BusinessAssessmentStatus.DATA_COLLECTION, actor_id)

    def update_title(self, new_title: str, actor_id: UUID | None = None) -> None:
        value = _required_text(new_title, "title", 200)
        if value == self.title:
            return
        old = self.title
        self.title = value
        self._touch()
        self._emit(BusinessAssessmentUpdated(
            uuid4(), self.updated_at, self.id, actor_id, old, value
        ))
