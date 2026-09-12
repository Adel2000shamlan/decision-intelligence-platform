from app.modules.risk.domain.models import Risk
from app.modules.risk.domain.services import RiskDomainService
class RiskApplicationService:
    def __init__(self,repository=None):
        from app.modules.risk.persistence.repository import RiskRepository
        self.repository=repository or RiskRepository(); self.domain=RiskDomainService()
    def create(self,project_id,title,description='',decision_id=None,source='human',actor_id=None): return self.domain.create(self.repository,UUID(str(project_id)),title,description,UUID(str(decision_id)) if decision_id else None,source,actor_id).entity
    def get(self,i): return self.repository.get_by_id(i)
    def list_by_project(self,p): return self.repository.list_by_project(p)
