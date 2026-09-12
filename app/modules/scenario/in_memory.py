from app.shared.domain.errors import EntityNotFound
from .domain.models import Scenario
from .domain.repository import ScenarioRepository
class InMemoryScenarioRepository(ScenarioRepository):
    def __init__(self): self._items={}
    def get_by_id(self,scenario_id): return self._items.get(scenario_id)
    def list_by_decision(self,decision_id): return [x for x in self._items.values() if x.decision_id==decision_id]
    def list_by_option(self,option_id): return [x for x in self._items.values() if x.option_id==option_id]
    def exists_by_name(self,decision_id,name): return any(x.decision_id==decision_id and x.name.casefold()==name.strip().casefold() and x.status is not __import__('app.modules.scenario.domain.models',fromlist=['ScenarioStatus']).ScenarioStatus.ARCHIVED for x in self._items.values())
    def save(self,scenario): self._items[scenario.id]=scenario; return scenario

def require_scenario(repo,scenario_id):
    item=repo.get_by_id(scenario_id)
    if item is None: raise EntityNotFound(f'scenario not found: {scenario_id}')
    return item
