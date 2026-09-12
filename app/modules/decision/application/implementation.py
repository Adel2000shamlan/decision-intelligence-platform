from dataclasses import dataclass, field
from uuid import uuid4, UUID
@dataclass
class DecisionApplicationService:
    store:dict = field(default_factory=dict)
    def create(self, payload:dict, actor_id:UUID|None=None):
        item={'id':str(uuid4()),'actor_id':str(actor_id) if actor_id else None,'payload':dict(payload)}
        self.store[item['id']]=item; return item
    def get(self,item_id:str): return self.store.get(item_id)
    def list(self): return list(self.store.values())
