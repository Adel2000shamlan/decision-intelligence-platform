from uuid import UUID
from app.modules.scenario.domain.services import ScenarioDomainService
class ScenarioApplicationService:
    def __init__(self,repository=None,decision_repository=None,option_repository=None):
        from app.modules.scenario.persistence.repository import ScenarioRepository
        self.repository=repository or ScenarioRepository(); self.decisions=decision_repository; self.options=option_repository; self.domain=ScenarioDomainService()
    def create(self,decision_id,option_id,name,**kwargs):
        if not self.decisions or not self.options: raise RuntimeError('decision and option repositories are required')
        return self.domain.create(self.repository,self.decisions,self.options,UUID(str(decision_id)),UUID(str(option_id)),name,**kwargs).entity
    def get(self,i): return self.repository.get_by_id(i)
    def list_by_decision(self,d): return self.repository.list_by_decision(d)
