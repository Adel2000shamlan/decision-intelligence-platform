from __future__ import annotations

from dataclasses import fields, is_dataclass
from datetime import datetime, timezone
from typing import Iterable
from uuid import UUID

from .errors import InvalidDomainData, BusinessRuleViolation


class DomainValidationError(InvalidDomainData):
    """Raised when a domain object violates the structural contract."""


class DomainValidator:
    """Deterministic validation boundary for domain objects.

    Validation is side-effect free: it never mutates aggregates or consumes events.
    """

    @staticmethod
    def validate_uuid(value: object, field_name: str) -> None:
        if not isinstance(value, UUID):
            raise DomainValidationError(f"{field_name} must be UUID")

    @staticmethod
    def validate_version(value: object) -> None:
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise DomainValidationError("version must be integer >= 1")

    @staticmethod
    def validate_timestamp(value: object, field_name: str) -> None:
        if not isinstance(value, datetime):
            raise DomainValidationError(f"{field_name} must be datetime")
        if value.tzinfo is None or value.utcoffset() is None:
            raise DomainValidationError(f"{field_name} must be timezone-aware")

    @classmethod
    def validate_aggregate(cls, aggregate: object) -> None:
        for field_name in ("id", "version", "created_at", "updated_at"):
            if not hasattr(aggregate, field_name):
                raise DomainValidationError(f"aggregate missing {field_name}")
        cls.validate_uuid(getattr(aggregate, "id"), "id")
        cls.validate_version(getattr(aggregate, "version"))
        cls.validate_timestamp(getattr(aggregate, "created_at"), "created_at")
        cls.validate_timestamp(getattr(aggregate, "updated_at"), "updated_at")
        if getattr(aggregate, "updated_at") < getattr(aggregate, "created_at"):
            raise DomainValidationError("updated_at cannot precede created_at")
        pending = getattr(aggregate, "_pending_events", None)
        if not isinstance(pending, list):
            raise DomainValidationError("_pending_events must be a list")
        for event in pending:
            cls.validate_event(event, getattr(aggregate, "id"))
        invariant = getattr(aggregate, "validate_invariants", None)
        if not callable(invariant):
            raise DomainValidationError("aggregate must expose validate_invariants()")
        invariant()

    @classmethod
    def validate_event(cls, event: object, aggregate_id: UUID | None = None) -> None:
        if not is_dataclass(event):
            raise DomainValidationError("domain event must be a dataclass instance")
        for field_name in ("event_id", "occurred_at", "aggregate_id", "actor_id"):
            if not hasattr(event, field_name):
                raise DomainValidationError(f"event missing {field_name}")
        cls.validate_uuid(event.event_id, "event_id")
        cls.validate_uuid(event.aggregate_id, "aggregate_id")
        cls.validate_timestamp(event.occurred_at, "occurred_at")
        if event.actor_id is not None:
            cls.validate_uuid(event.actor_id, "actor_id")
        if aggregate_id is not None and event.aggregate_id != aggregate_id:
            raise DomainValidationError("event aggregate_id does not match aggregate")

    @classmethod
    def validate_event_sequence(cls, events: Iterable[object], aggregate_id: UUID) -> None:
        seen: set[UUID] = set()
        previous_time: datetime | None = None
        for event in events:
            cls.validate_event(event, aggregate_id)
            if event.event_id in seen:
                raise DomainValidationError("duplicate event_id in event sequence")
            seen.add(event.event_id)
            if previous_time is not None and event.occurred_at < previous_time:
                raise DomainValidationError("event timestamps must be monotonic")
            previous_time = event.occurred_at

    @classmethod
    def validate_time_now(cls, value: datetime, field_name: str) -> None:
        cls.validate_timestamp(value, field_name)
        if value > datetime.now(timezone.utc):
            raise DomainValidationError(f"{field_name} cannot be in the future")

    @classmethod
    def validate_string(cls, value: object, field_name: str, max_length: int) -> None:
        if not isinstance(value, str) or not value.strip():
            raise DomainValidationError(f"{field_name} must be non-empty string")
        if len(value.strip()) > max_length:
            raise DomainValidationError(f"{field_name} exceeds {max_length} characters")

    @classmethod
    def validate_probability_1_5(cls, value: object, field_name: str) -> None:
        if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 5:
            raise DomainValidationError(f"{field_name} must be integer 1..5")

    @classmethod
    def validate_numeric_bounds(cls, value: object, field_name: str, low: float, high: float) -> None:
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not low <= value <= high:
            raise DomainValidationError(f"{field_name} must be between {low} and {high}")
