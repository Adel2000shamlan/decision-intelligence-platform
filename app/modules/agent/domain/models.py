from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4
@dataclass
class Agent:
    id: UUID; tenant_id: UUID; name: str; capabilities: frozenset[str]; enabled: bool=True; created_at: datetime=field(default_factory=lambda:datetime.now(timezone.utc))
    @classmethod
    def register(cls,tenant_id,name,capabilities=()):
        if not str(name).strip(): raise ValueError('agent name required')
        return cls(uuid4(),UUID(str(tenant_id)),str(name).strip(),frozenset(str(x) for x in capabilities))
    def disable(self): self.enabled=False
    def enable(self): self.enabled=True
