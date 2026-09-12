from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4

@dataclass
class KPI:
    id: UUID
    tenant_id: UUID
    name: str
    unit: str
    target: float
    actual: float
    project_id: UUID|None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    version: int = 1
    @classmethod
    def create(cls, tenant_id, name, unit, target, actual=0, project_id=None):
        if not str(name).strip() or not str(unit).strip(): raise ValueError('name and unit are required')
        return cls(uuid4(), UUID(str(tenant_id)), str(name).strip(), str(unit).strip(), float(target), float(actual), UUID(str(project_id)) if project_id else None)
    @property
    def achievement_ratio(self):
        return 0.0 if self.target == 0 else self.actual / self.target
    def update(self, *, actual=None, target=None):
        if actual is not None: self.actual=float(actual)
        if target is not None: self.target=float(target)
        self.updated_at=datetime.now(timezone.utc); self.version += 1
