from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from .confidence import Confidence
from .evidence import Evidence


@dataclass(frozen=True, slots=True)
class IntelligenceResult:
    tenant_id: UUID
    actor_id: UUID
    correlation_id: UUID
    result: Any
    evidence: tuple[Evidence, ...]
    confidence: Confidence
    confirmed_facts: tuple[str, ...] = ()
    assumptions: tuple[str, ...] = ()
    estimates: tuple[str, ...] = ()
    human_review_required: bool = True

    def __post_init__(self) -> None:
        if not isinstance(self.tenant_id, UUID):
            raise ValueError("tenant_id must be UUID")

        if not isinstance(self.actor_id, UUID):
            raise ValueError("actor_id must be UUID")

        if not isinstance(self.correlation_id, UUID):
            raise ValueError("correlation_id must be UUID")

        if not isinstance(self.confidence, Confidence):
            raise ValueError("confidence must be Confidence")

        if not isinstance(self.evidence, tuple):
            raise ValueError("evidence must be immutable tuple")

        if not all(isinstance(item, Evidence) for item in self.evidence):
            raise ValueError("evidence must contain Evidence items")

        for name in ("confirmed_facts", "assumptions", "estimates"):
            value = getattr(self, name)
            if not isinstance(value, tuple):
                raise ValueError(f"{name} must be immutable tuple")

            if not all(isinstance(item, str) and item.strip() for item in value):
                raise ValueError(f"{name} must contain non-empty strings")

        if not isinstance(self.human_review_required, bool):
            raise ValueError("human_review_required must be bool")
