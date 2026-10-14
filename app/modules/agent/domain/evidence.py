from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.modules.intelligence.domain.evidence import Evidence


@dataclass(frozen=True, slots=True)
class AgentEvidenceSet:
    """Validated evidence boundary for an agent execution."""

    tenant_id: UUID
    evidence: tuple[Evidence, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.tenant_id, UUID):
            raise ValueError("tenant_id must be UUID")

        if not isinstance(self.evidence, tuple):
            raise ValueError("evidence must be immutable tuple")

        for item in self.evidence:
            if not isinstance(item, Evidence):
                raise ValueError("evidence must contain Evidence values")
            if item.tenant_id != self.tenant_id:
                raise ValueError("evidence tenant mismatch")
            if not item.traceable:
                raise ValueError("evidence must be traceable")

    @property
    def evidence_ids(self) -> tuple[UUID, ...]:
        return tuple(item.evidence_id for item in self.evidence)

    def require(self) -> tuple[Evidence, ...]:
        if not self.evidence:
            raise ValueError("execution evidence is required")
        return self.evidence
