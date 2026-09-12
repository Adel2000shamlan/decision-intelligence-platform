from dataclasses import dataclass, field
from datetime import datetime, timezone
import uuid
@dataclass(frozen=True)
class StoredEvent:
    event_id:str; event_type:str; aggregate_id:str; payload:dict; occurred_at:datetime=field(default_factory=lambda:datetime.now(timezone.utc)); correlation_id:str|None=None
class EventStore:
    def __init__(self): self._events=[]; self._seen=set()
    def append(self,event:StoredEvent):
        if event.event_id in self._seen: return False
        self._seen.add(event.event_id); self._events.append(event); return True
    def all(self): return tuple(self._events)
class EventBus:
    def __init__(self): self._handlers={}
    def subscribe(self,t,h): self._handlers.setdefault(t,[]).append(h)
    def publish(self,event):
        for h in self._handlers.get(event.event_type,[]): h(event)
