from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from uuid import UUID, uuid4

from app.shared.domain.errors import InvalidDomainData


class MemoryType(str, Enum):
    FACT = "fact"
    OBSERVATION = "observation"
    PREFERENCE = "preference"
    DECISION = "decision"
    INSIGHT = "insight"
    ASSUMPTION = "assumption"


class MemoryStatus(str, Enum):
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    ARCHIVED = "archived"


@dataclass(frozen=True)
class MemoryItem:
    id: UUID
    tenant_id: UUID
    memory_type: MemoryType
    content: str
    source: str
    evidence_ids: tuple[UUID, ...]
    confidence: float | None
    status: MemoryStatus
    created_at: datetime
    expires_at: datetime | None
    version: int

    @classmethod
    def create(
        cls,
        tenant_id,
        memory_type,
        content,
        source,
        evidence_ids=(),
        confidence=None,
        expires_at=None,
    ):
        if not isinstance(tenant_id, UUID):
            raise InvalidDomainData("tenant_id must be UUID")

        try:
            memory_type = MemoryType(memory_type)
        except (TypeError, ValueError) as exc:
            raise InvalidDomainData("invalid memory type") from exc

        if not isinstance(content, str) or not content.strip():
            raise InvalidDomainData("memory content is required")

        if not isinstance(source, str) or not source.strip():
            raise InvalidDomainData("memory source is required")

        if not isinstance(evidence_ids, tuple):
            evidence_ids = tuple(evidence_ids)

        if any(not isinstance(item, UUID) for item in evidence_ids):
            raise InvalidDomainData("evidence_ids must contain UUID values")

        if confidence is not None:
            if (
                isinstance(confidence, bool)
                or not isinstance(confidence, (int, float))
                or not 0 <= float(confidence) <= 1
            ):
                raise InvalidDomainData(
                    "confidence must be numeric between 0 and 1"
                )
            confidence = float(confidence)

        created_at = datetime.now(timezone.utc)

        if expires_at is not None:
            if not isinstance(expires_at, datetime) or expires_at.tzinfo is None:
                raise InvalidDomainData(
                    "expires_at must be timezone-aware datetime"
                )
            if expires_at <= created_at:
                raise InvalidDomainData(
                    "expires_at must be after created_at"
                )

        return cls(
            id=uuid4(),
            tenant_id=tenant_id,
            memory_type=memory_type,
            content=content.strip(),
            source=source.strip(),
            evidence_ids=evidence_ids,
            confidence=confidence,
            status=MemoryStatus.ACTIVE,
            created_at=created_at,
            expires_at=expires_at,
            version=1,
        )
