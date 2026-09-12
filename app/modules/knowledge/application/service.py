from app.modules.knowledge.domain.models import KnowledgeItem
class KnowledgeApplicationService:
    def __init__(self,repository=None):
        from app.modules.knowledge.persistence.repository import KnowledgeRepository
        self.repository=repository or KnowledgeRepository()
    def create(self,tenant_id,title,content,source,project_id=None,evidence_uri=None): return self.repository.save(KnowledgeItem.create(tenant_id,title,content,source,project_id,evidence_uri))
    def get(self,item_id): return self.repository.get(item_id)
    def list(self,tenant_id): return self.repository.list(tenant_id)
