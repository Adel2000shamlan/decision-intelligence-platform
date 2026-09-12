from dataclasses import dataclass
from uuid import UUID
@dataclass(frozen=True)
class ProjectAuditRecord:
    project_id: UUID; actor_id: UUID|None; action: str; version: int
class ProjectEventPublisher:
    def __init__(self): self.events=[]; self._ids=set()
    def publish(self,event):
        key=getattr(event,'event_id',None)
        if key in self._ids: return False
        if key is not None: self._ids.add(key)
        self.events.append(event); return True
class ProjectAuditSink:
    def __init__(self): self.records=[]
    def record(self,project_id,actor_id,action,version): self.records.append(ProjectAuditRecord(project_id,actor_id,action,version))
