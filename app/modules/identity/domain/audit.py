from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID, uuid4
from app.modules.identity.domain.security import CredentialBoundaryContract

@dataclass(frozen=True, slots=True)
class SecurityAuditEvent:
    event_id: UUID
    event_type: str
    occurred_at: datetime
    actor_id: UUID | None
    target_user_id: UUID | None
    correlation_id: UUID
    outcome: str
    metadata: tuple[tuple[str, str], ...] = ()
    def __post_init__(self):
        if self.outcome not in {"success", "failure", "blocked"}: raise ValueError("invalid audit outcome")
        CredentialBoundaryContract.assert_event_safe(self)

class SecurityAuditSink:
    def record(self, event: SecurityAuditEvent) -> None: raise NotImplementedError

class InMemorySecurityAuditSink(SecurityAuditSink):
    def __init__(self): self.events=[]
    def record(self,event):
        CredentialBoundaryContract.assert_event_safe(event)
        self.events.append(event)
