from uuid import UUID
from app.modules.execution.domain.services import ExecutionDomainService
class ExecutionApplicationService:
    def __init__(self,repository=None):
        from app.modules.execution.persistence.repository import ExecutionRepository
        self.repository=repository or ExecutionRepository(); self.domain=ExecutionDomainService()
    def create(self,project_id,title,description='',**kwargs): return self.domain.create(self.repository,UUID(str(project_id)),title,description,**kwargs).entity
    def get(self,i): return self.repository.get_by_id(i)
    def list_by_project(self,p): return self.repository.list_by_project(p)
