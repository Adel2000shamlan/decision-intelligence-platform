from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4
@dataclass(frozen=True)
class AIRequest:
    id: UUID; tenant_id: UUID; actor_id: UUID; task: str; model: str; created_at: datetime=field(default_factory=lambda:datetime.now(timezone.utc))
    @classmethod
    def create(cls,tenant_id,actor_id,task,model):
        if not str(task).strip() or not str(model).strip(): raise ValueError('task and model are required')
        return cls(uuid4(),UUID(str(tenant_id)),UUID(str(actor_id)),str(task).strip(),str(model).strip())
