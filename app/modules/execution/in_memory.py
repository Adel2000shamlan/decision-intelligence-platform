from uuid import UUID
class InMemoryExecutionRepository:
 def __init__(self): self.items={}
 def get_by_id(self,execution_id): return self.items.get(execution_id)
 def list_by_project(self,project_id): return [x for x in self.items.values() if x.project_id==project_id]
 def exists_by_title(self,project_id,title,exclude_id=None): return any(x.project_id==project_id and x.title.casefold()==title.strip().casefold() and x.id!=exclude_id for x in self.items.values())
 def save(self,execution): self.items[execution.id]=execution; return execution
