from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from uuid import UUID


class EvidenceType(str, Enum):
    FACT = "fact"
    SOURCE = "source"
    DOCUMENT = "document"
    OBSERVATION = "observation"
    ASSUMPTION = "assumption"


@dataclass(frozen=True, slots=True)
class Evidence:
    evidence_id: UUID
    tenant_id: UUID
    evidence_type: EvidenceType
    source: str
    reference: str
    statement: str
    traceable: bool = True

    def __post_init__(self) -> None:
        if not isinstance(self.evidence_id, UUID):
            raise ValueError("evidence_id must be UUID")
        if not isinstance(self.tenant_id, UUID):
            raise ValueError("tenant_id must be UUID")

        object.__setattr__(
            self,
            "evidence_type",
            EvidenceType(self.evidence_type),
        )

        for name in ("source", "reference", "statement"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} is required")

        if not isinstance(self.traceable, bool):
            raise ValueError("traceable must be bool")
