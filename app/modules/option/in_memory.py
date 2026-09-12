from uuid import UUID
from app.shared.domain.errors import EntityNotFound
from .domain.models import Option
from .domain.repository import OptionRepository
class InMemoryOptionRepository(OptionRepository):
    def __init__(self): self._items={}
    def get_by_id(self,option_id): return self._items.get(option_id)
    def list_by_decision(self,decision_id): return [x for x in self._items.values() if x.decision_id==decision_id]
    def exists_by_title(self,decision_id,title): return any(x.decision_id==decision_id and x.title.casefold()==title.strip().casefold() and x.status.value!='archived' for x in self._items.values())
    def save(self,option): self._items[option.id]=option; return option

def require_option(repo,option_id):
    item=repo.get_by_id(option_id)
    if item is None: raise EntityNotFound(f'option not found: {option_id}')
    return item
