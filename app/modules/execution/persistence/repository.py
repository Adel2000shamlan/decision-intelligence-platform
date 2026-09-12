from uuid import UUID
from app.modules.execution.domain.models import Execution
class ExecutionRepository:
    def __init__(self): self.items={}
    def save(self,item:Execution): self.items[item.id]=item; return item
    def get_by_id(self,item_id): return self.items.get(UUID(str(item_id)))
    def list_by_project(self,project_id): return [x for x in self.items.values() if x.project_id==UUID(str(project_id))]
    def exists_by_title(self,project_id,title,exclude_id=None): return any(x.project_id==UUID(str(project_id)) and x.title.casefold()==str(title).strip().casefold() and x.id!=exclude_id for x in self.items.values())
