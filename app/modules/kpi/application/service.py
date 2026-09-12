from uuid import UUID
from app.modules.kpi.domain.models import KPI
class KPIApplicationService:
    def __init__(self, repository=None):
        from app.modules.kpi.persistence.repository import KPIRepository
        self.repository=repository or KPIRepository()
    def create(self, tenant_id, name, unit, target, actual=0, project_id=None): return self.repository.save(KPI.create(tenant_id,name,unit,target,actual,project_id))
    def get(self,kpi_id): return self.repository.get(kpi_id)
    def list(self,tenant_id): return self.repository.list(tenant_id)
    def update(self,kpi_id,**changes):
        k=self.repository.get(kpi_id)
        if not k: raise LookupError('kpi not found')
        k.update(**changes); return self.repository.save(k)
