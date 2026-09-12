from .domain.models import Decision
from .domain.repository import DecisionRepository
class InMemoryDecisionRepository(DecisionRepository):
    def __init__(self): self._items={}
    def get_by_id(self,decision_id): return self._items.get(decision_id)
    def list_by_project(self,project_id): return [d for d in self._items.values() if d.project_id==project_id]
    def list_by_organization(self,organization_id): return [d for d in self._items.values() if d.organization_id==organization_id]
    def exists_by_title(self,project_id,title): return any(d.project_id==project_id and d.title==(title.strip() if isinstance(title,str) else title) for d in self._items.values())
    def save(self,decision): self._items[decision.id]=decision; return decision
class DefaultDecisionFactory:
    def create(self,organization_id,project_id,title,description='',decision_type='strategic',priority='medium',actor_id=None): return Decision.create(organization_id,project_id,title,description,decision_type,priority,actor_id)
