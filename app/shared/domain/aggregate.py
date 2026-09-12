from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, Protocol, TypeVar
from uuid import UUID

from app.shared.domain.errors import BusinessRuleViolation, InvalidDomainData

T = TypeVar("T")


class AggregateRootProtocol(Protocol):
    id: UUID
    version: int

    def pull_events(self) -> tuple[object, ...]: ...

    def validate_invariants(self) -> None: ...


class AggregateRoot:
    """Common aggregate-root contract without persistence/framework coupling.

    Concrete domain aggregates keep their own dataclass fields and event queue;
    this class supplies the cross-domain consistency contract only.
    """

    def validate_invariants(self) -> None:
        if not isinstance(self.id, UUID):
            raise InvalidDomainData("aggregate id must be UUID")
        if not isinstance(self.version, int) or self.version < 1:
            raise InvalidDomainData("aggregate version must be an integer >= 1")

    @property
    def aggregate_id(self) -> UUID:
        return self.id

    @property
    def aggregate_version(self) -> int:
        return self.version

    def assert_version(self, expected_version: int) -> None:
        if expected_version != self.version:
            raise BusinessRuleViolation(
                f"aggregate version conflict: expected {expected_version}, current {self.version}"
            )


@dataclass(frozen=True)
class AggregateSnapshot(Generic[T]):
    """Immutable hand-off used by application/persistence boundaries."""

    aggregate_id: UUID
    version: int
    state: T


class AggregateBoundary:
    """Guards an aggregate before it crosses an application boundary."""

    @staticmethod
    def validate(root: AggregateRootProtocol) -> None:
        root.validate_invariants()
        events = root.pull_events()
        # Put events back when a boundary check is only validating. Concrete
        # roots expose an internal queue; this keeps validation side-effect free.
        queue = getattr(root, "_pending_events", None)
        if queue is not None:
            queue.extend(events)
