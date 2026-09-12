from __future__ import annotations

from typing import Any
from uuid import UUID

from app.shared.domain.aggregate import AggregateRoot
from app.shared.domain.errors import BusinessRuleViolation


class AggregateRegistry:
    """Small deterministic registry for aggregate instances in tests/adapters.

    It intentionally does not become a persistence mechanism. Its job is to
    enforce one-root-per-identity semantics at the application boundary.
    """

    def __init__(self) -> None:
        self._items: dict[UUID, AggregateRoot] = {}

    def add(self, aggregate: AggregateRoot) -> None:
        aggregate.validate_invariants()
        existing = self._items.get(aggregate.aggregate_id)
        if existing is not None and existing is not aggregate:
            raise BusinessRuleViolation("aggregate id already registered")
        self._items[aggregate.aggregate_id] = aggregate

    def get(self, aggregate_id: UUID) -> AggregateRoot | None:
        return self._items.get(aggregate_id)

    def remove(self, aggregate_id: UUID) -> None:
        self._items.pop(aggregate_id, None)

    def __len__(self) -> int:
        return len(self._items)
