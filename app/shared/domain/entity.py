from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4
@dataclass
class Entity:
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    version: int = 1
    def touch(self): self.updated_at=datetime.now(timezone.utc); self.version+=1
