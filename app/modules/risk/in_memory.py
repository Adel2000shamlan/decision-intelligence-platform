from uuid import UUID
from .domain.models import Risk
from .domain.repository import RiskRepository
class InMemoryRiskRepository(RiskRepository):
    def __init__(self): self._items={}
    def get_by_id(self,risk_id): return self._items.get(risk_id)
    def list_by_project(self,project_id): return [r for r in self._items.values() if r.project_id==project_id]
    def list_by_decision(self,decision_id): return [r for r in self._items.values() if r.decision_id==decision_id]
    def exists_by_title(self,project_id,title): return any(r.project_id==project_id and r.title==(title.strip() if isinstance(title,str) else title) for r in self._items.values())
    def save(self,risk): self._items[risk.id]=risk; return risk
class DefaultRiskFactory:
    def create(self,project_id,title,description='',decision_id=None,source='human',actor_id=None): return Risk.create(project_id,title,description,decision_id,source,actor_id)
