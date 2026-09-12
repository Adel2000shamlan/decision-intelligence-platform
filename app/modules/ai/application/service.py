from app.modules.ai.domain.models import AIRequest
class AIApplicationService:
    def __init__(self): self.requests={}
    def submit(self,tenant_id,actor_id,task,model):
        r=AIRequest.create(tenant_id,actor_id,task,model); self.requests[r.id]=r; return r
    def get(self,i): return self.requests.get(i)
    def list(self,tenant_id): return [r for r in self.requests.values() if r.tenant_id==tenant_id]
