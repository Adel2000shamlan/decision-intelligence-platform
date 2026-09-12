from dataclasses import dataclass, field
from datetime import datetime, timezone
class InMemoryOrganizationEventPublisher:
    def __init__(self): self.events=[]; self._ids=set()
    def publish(self,event):
        key=getattr(event,'event_id',id(event))
        if key not in self._ids: self._ids.add(key); self.events.append(event)
@dataclass
class OrganizationAuditSink:
    records:list=field(default_factory=list)
    def record(self, organization_id, actor_id, action, version): self.records.append({'organization_id':str(organization_id),'actor_id':str(actor_id) if actor_id else None,'action':action,'version':version,'at':datetime.now(timezone.utc).isoformat()})
