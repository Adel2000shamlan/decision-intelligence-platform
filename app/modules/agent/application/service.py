from app.modules.agent.domain.models import Agent
class AgentApplicationService:
    def __init__(self,repository=None):
        from app.modules.agent.persistence.repository import AgentRepository
        self.repository=repository or AgentRepository()
    def register(self,tenant_id,name,capabilities=()): return self.repository.save(Agent.register(tenant_id,name,capabilities))
    def get(self,i): return self.repository.get(i)
    def list(self,t): return self.repository.list(t)
