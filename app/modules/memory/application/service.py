from uuid import UUID

from app.shared.domain.errors import BusinessRuleViolation

from ..domain.models import MemoryItem, MemoryStatus, MemoryType
from ..persistence.repository import MemoryRepository


class MemoryService:
    def __init__(self, repository: MemoryRepository):
        self.repository = repository

    def remember(
        self,
        *,
        tenant_id: UUID,
        memory_type: MemoryType,
        content: str,
        source: str,
        evidence_ids: tuple[UUID, ...] = (),
        confidence: float | None = None,
        expires_at=None,
    ) -> MemoryItem:
        item = MemoryItem.create(
            tenant_id=tenant_id,
            memory_type=memory_type,
            content=content,
            source=source,
            evidence_ids=evidence_ids,
            confidence=confidence,
            expires_at=expires_at,
        )
        return self.repository.save(item)

    def get(self, tenant_id: UUID, memory_id: UUID) -> MemoryItem | None:
        return self.repository.get(tenant_id, memory_id)

    def list(
        self,
        tenant_id: UUID,
        *,
        memory_type: MemoryType | None = None,
        status: MemoryStatus | None = None,
    ) -> tuple[MemoryItem, ...]:
        return self.repository.list(
            tenant_id,
            memory_type=memory_type,
            status=status,
        )

    def supersede(
        self,
        *,
        tenant_id: UUID,
        memory_id: UUID,
        content: str,
        source: str,
        evidence_ids: tuple[UUID, ...] = (),
        confidence: float | None = None,
        expires_at=None,
    ) -> MemoryItem:
        current = self.repository.get(tenant_id, memory_id)

        if current is None:
            raise BusinessRuleViolation("memory item not found")

        if current.status is not MemoryStatus.ACTIVE:
            raise BusinessRuleViolation(
                "only active memory can be superseded"
            )

        replacement = MemoryItem(
            id=current.id,
            tenant_id=current.tenant_id,
            memory_type=current.memory_type,
            content=content,
            source=source,
            evidence_ids=evidence_ids,
            confidence=confidence,
            status=MemoryStatus.SUPERSEDED,
            created_at=current.created_at,
            expires_at=expires_at,
            version=current.version + 1,
        )

        return self.repository.save(replacement)

    def archive(self, tenant_id: UUID, memory_id: UUID) -> MemoryItem:
        current = self.repository.get(tenant_id, memory_id)

        if current is None:
            raise BusinessRuleViolation("memory item not found")

        if current.status is MemoryStatus.ARCHIVED:
            return current

        archived = MemoryItem(
            id=current.id,
            tenant_id=current.tenant_id,
            memory_type=current.memory_type,
            content=current.content,
            source=current.source,
            evidence_ids=current.evidence_ids,
            confidence=current.confidence,
            status=MemoryStatus.ARCHIVED,
            created_at=current.created_at,
            expires_at=current.expires_at,
            version=current.version + 1,
        )

        return self.repository.save(archived)

    def forget(self, tenant_id: UUID, memory_id: UUID) -> None:
        self.repository.delete(tenant_id, memory_id)
