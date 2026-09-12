from dataclasses import dataclass
from uuid import UUID
from app.shared.domain.errors import EntityNotFound, BusinessRuleViolation
from .ports import DecisionUnitOfWork
from ..domain.models import DecisionType,DecisionPriority
@dataclass(frozen=True)
class CreateDecision: organization_id:UUID; project_id:UUID; title:str; description:str=''; decision_type:DecisionType=DecisionType.STRATEGIC; priority:DecisionPriority=DecisionPriority.MEDIUM; actor_id:UUID|None=None
@dataclass(frozen=True)
class StartDecisionAnalysis: decision_id:UUID; actor_id:UUID|None=None
@dataclass(frozen=True)
class SubmitDecisionForApproval: decision_id:UUID; actor_id:UUID|None=None
@dataclass(frozen=True)
class ApproveDecision: decision_id:UUID; actor_id:UUID|None=None
@dataclass(frozen=True)
class RejectDecision: decision_id:UUID; reason:str|None=None; actor_id:UUID|None=None
@dataclass(frozen=True)
class CancelDecision: decision_id:UUID; reason:str|None=None; actor_id:UUID|None=None
@dataclass(frozen=True)
class ExecuteDecision: decision_id:UUID; actor_id:UUID|None=None
@dataclass(frozen=True)
class CloseDecision: decision_id:UUID; actor_id:UUID|None=None
@dataclass(frozen=True)
class UpdateDecision: decision_id:UUID; field_name:str; value:object; actor_id:UUID|None=None
class DecisionCommandHandler:
    def __init__(self,uow:DecisionUnitOfWork): self.uow=uow
    def _get(self,i):
        d=self.uow.repository.get_by_id(i)
        if d is None: raise EntityNotFound(f'decision not found: {i}')
        return d
    def _save(self,d): self.uow.repository.save(d); self.uow.commit(); return d
    def create(self,c):
        d=self.uow.factory.create(c.organization_id,c.project_id,c.title,c.description,c.decision_type,c.priority,c.actor_id); self.uow.policy.ensure_unique_title(self.uow.repository,d); return self._save(d)
    def start_analysis(self,c): return self._mut(self._get(c.decision_id),lambda d:d.start_analysis(c.actor_id))
    def submit_for_approval(self,c):
        d=self._get(c.decision_id); self.uow.policy.ensure_can_submit(d); d.submit_for_approval(c.actor_id); return self._save(d)
    def approve(self,c):
        d=self._get(c.decision_id); self.uow.policy.ensure_can_approve(d); d.approve(c.actor_id); return self._save(d)
    def reject(self,c): return self._mut(self._get(c.decision_id),lambda d:d.reject(c.reason,c.actor_id))
    def cancel(self,c): return self._mut(self._get(c.decision_id),lambda d:d.cancel(c.reason,c.actor_id))
    def execute(self,c): return self._mut(self._get(c.decision_id),lambda d:d.execute(c.actor_id))
    def close(self,c): return self._mut(self._get(c.decision_id),lambda d:d.close(c.actor_id))
    def update(self,c):
        d=self._get(c.decision_id)
        if c.field_name=='title' and isinstance(c.value,str) and c.value.strip()!=d.title and self.uow.repository.exists_by_title(d.project_id,c.value): raise BusinessRuleViolation(f'decision title already exists in project: {c.value.strip()}')
        d.update(c.field_name,c.value,c.actor_id); return self._save(d)
    def _mut(self,d,fn): fn(d); return self._save(d)
