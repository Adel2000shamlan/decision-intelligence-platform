from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from uuid import UUID, uuid4


class SupportPriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class SupportStatus(str, Enum):
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    CLOSED = "closed"


@dataclass(frozen=True, slots=True)
class SupportTicket:
    id: UUID
    tenant_id: UUID
    reporter_id: UUID
    title: str
    description: str
    priority: SupportPriority
    status: SupportStatus
    created_at: datetime
    acknowledged_at: datetime | None = None
    resolved_at: datetime | None = None

    @classmethod
    def create(
        cls,
        tenant_id: UUID,
        reporter_id: UUID,
        title: str,
        description: str,
        priority: SupportPriority = SupportPriority.NORMAL,
    ) -> "SupportTicket":
        if not title.strip():
            raise ValueError("support ticket title must not be empty")
        if not description.strip():
            raise ValueError("support ticket description must not be empty")
        return cls(
            id=uuid4(),
            tenant_id=tenant_id,
            reporter_id=reporter_id,
            title=title.strip(),
            description=description.strip(),
            priority=priority,
            status=SupportStatus.OPEN,
            created_at=datetime.now(timezone.utc),
        )

    def acknowledge(self) -> "SupportTicket":
        if self.status != SupportStatus.OPEN:
            raise ValueError("only open tickets can be acknowledged")
        return SupportTicket(
            id=self.id,
            tenant_id=self.tenant_id,
            reporter_id=self.reporter_id,
            title=self.title,
            description=self.description,
            priority=self.priority,
            status=SupportStatus.ACKNOWLEDGED,
            created_at=self.created_at,
            acknowledged_at=datetime.now(timezone.utc),
            resolved_at=self.resolved_at,
        )

    def resolve(self) -> "SupportTicket":
        if self.status != SupportStatus.ACKNOWLEDGED:
            raise ValueError("only acknowledged tickets can be resolved")
        return SupportTicket(
            id=self.id,
            tenant_id=self.tenant_id,
            reporter_id=self.reporter_id,
            title=self.title,
            description=self.description,
            priority=self.priority,
            status=SupportStatus.RESOLVED,
            created_at=self.created_at,
            acknowledged_at=self.acknowledged_at,
            resolved_at=datetime.now(timezone.utc),
        )
