from dataclasses import dataclass
from uuid import UUID
from app.shared.domain.errors import EntityNotFound, BusinessRuleViolation
from .ports import RiskUnitOfWork
from ..domain.models import RiskSource
@dataclass(frozen=True)
class CreateRisk: project_id:UUID; title:str; description:str=''; decision_id:UUID|None=None; source:RiskSource=RiskSource.HUMAN; actor_id:UUID|None=None
@dataclass(frozen=True)
class IdentifyRisk: risk_id:UUID; actor_id:UUID|None=None
@dataclass(frozen=True)
class AssessRisk: risk_id:UUID; probability:int; impact:int; actor_id:UUID|None=None
@dataclass(frozen=True)
class StartRiskMitigation: risk_id:UUID; actor_id:UUID|None=None
@dataclass(frozen=True)
class MonitorRisk: risk_id:UUID; residual_probability:int; residual_impact:int; actor_id:UUID|None=None
@dataclass(frozen=True)
class AcceptRisk: risk_id:UUID; actor_id:UUID|None=None
@dataclass(frozen=True)
class CloseRisk: risk_id:UUID; actor_id:UUID|None=None
@dataclass(frozen=True)
class ArchiveRisk: risk_id:UUID; actor_id:UUID|None=None
@dataclass(frozen=True)
class RenameRisk: risk_id:UUID; title:str; actor_id:UUID|None=None
class RiskCommandHandler:
    def __init__(self,uow:RiskUnitOfWork): self.uow=uow
    def create(self,c):
        r=self.uow.factory.create(c.project_id,c.title,c.description,c.decision_id,c.source,c.actor_id); self.uow.policy.ensure_unique_title(self.uow.repository,r); self.uow.repository.save(r); self.uow.commit(); return r
    def _get(self,i):
        r=self.uow.repository.get_by_id(i)
        if r is None: raise EntityNotFound(f'risk not found: {i}')
        return r
    def identify(self,c): return self._mut(self._get(c.risk_id),lambda r:r.identify(c.actor_id))
    def assess(self,c):
        r=self._get(c.risk_id); self.uow.policy.ensure_can_assess(r); r.assess(c.probability,c.impact,c.actor_id); return self._save(r)
    def start_mitigation(self,c):
        r=self._get(c.risk_id); self.uow.policy.ensure_can_select_mitigation(r); r.start_mitigation(c.actor_id); return self._save(r)
    def monitor(self,c):
        r=self._get(c.risk_id)
        from ..domain.models import Risk
        Risk._validate_rating(c.residual_probability,'residual_probability'); Risk._validate_rating(c.residual_impact,'residual_impact')
        prospective=c.residual_probability*c.residual_impact
        if r.score is not None and prospective>r.score: raise BusinessRuleViolation('residual risk cannot exceed inherent risk without explicit override')
        r.monitor(c.residual_probability,c.residual_impact,c.actor_id); return self._save(r)
    def accept(self,c): return self._mut(self._get(c.risk_id),lambda r:r.accept(c.actor_id))
    def close(self,c): return self._mut(self._get(c.risk_id),lambda r:r.close(c.actor_id))
    def archive(self,c): return self._mut(self._get(c.risk_id),lambda r:r.archive(c.actor_id))
    def rename(self,c):
        r=self._get(c.risk_id); candidate=c.title.strip() if isinstance(c.title,str) else c.title
        if candidate!=r.title and self.uow.repository.exists_by_title(r.project_id,candidate): raise BusinessRuleViolation(f'risk title already exists in project: {candidate}')
        r.rename(c.title,c.actor_id); return self._save(r)
    def _save(self,r): self.uow.repository.save(r); self.uow.commit(); return r
    def _mut(self,r,fn): fn(r); return self._save(r)
