from uuid import UUID
from app.modules.scenario.domain.models import Scenario
class ScenarioRepository:
    def __init__(self): self.items={}
    def save(self,item:Scenario): self.items[item.id]=item; return item
    def get_by_id(self,item_id): return self.items.get(UUID(str(item_id)))
    def list_by_decision(self,decision_id): return [x for x in self.items.values() if x.decision_id==UUID(str(decision_id))]
    def list_by_option(self,option_id): return [x for x in self.items.values() if x.option_id==UUID(str(option_id))]
    def exists_by_name(self,decision_id,name): return any(x.decision_id==UUID(str(decision_id)) and x.name.casefold()==str(name).strip().casefold() for x in self.items.values())
