from dataclasses import dataclass
from uuid import UUID
from app.modules.scenario.domain.models import ScenarioType, ScenarioSource
from app.shared.domain.errors import EntityNotFound, BusinessRuleViolation
@dataclass(frozen=True)
class CreateScenario: decision_id:UUID; option_id:UUID; name:str; description:str=''; scenario_type:ScenarioType=ScenarioType.CUSTOM; source:ScenarioSource=ScenarioSource.HUMAN; probability:float|None=None; confidence:float|None=None; actor_id:UUID|None=None
@dataclass(frozen=True)
class UpdateScenario: scenario_id:UUID; actor_id:UUID|None=None; name:str|None=None; description:str|None=None; scenario_type:ScenarioType|None=None; source:ScenarioSource|None=None; probability:float|None=None; confidence:float|None=None
@dataclass(frozen=True)
class StartScenarioAnalysis: scenario_id:UUID; actor_id:UUID|None=None
@dataclass(frozen=True)
class EvaluateScenario: scenario_id:UUID; actor_id:UUID|None=None
@dataclass(frozen=True)
class ApproveScenario: scenario_id:UUID; actor_id:UUID|None=None
@dataclass(frozen=True)
class RejectScenario: scenario_id:UUID; actor_id:UUID|None=None
@dataclass(frozen=True)
class ArchiveScenario: scenario_id:UUID; actor_id:UUID|None=None
class ScenarioCommandHandler:
    def __init__(self,uow): self.uow=uow
    def _get(self,i):
        s=self.uow.repository.get_by_id(i)
        if s is None: raise EntityNotFound(f'scenario not found: {i}')
        return s
    def create(self,c):
        s=self.uow.factory.create(c.decision_id,c.option_id,c.name,c.description,c.scenario_type,c.source,c.probability,c.confidence,c.actor_id)
        self.uow.policy.ensure_unique_name(self.uow.repository,s); self.uow.repository.save(s); self.uow.commit(); return s
    def _save(self,s): self.uow.repository.save(s); self.uow.commit(); return s
    def start_analysis(self,c):
        s=self._get(c.scenario_id); self.uow.policy.ensure_can_start_analysis(s); s.start_analysis(c.actor_id); return self._save(s)
    def evaluate(self,c):
        s=self._get(c.scenario_id); self.uow.policy.ensure_can_evaluate(s); s.evaluate(c.actor_id); return self._save(s)
    def approve(self,c):
        s=self._get(c.scenario_id); self.uow.policy.ensure_can_approve(s,c.actor_id); s.approve(c.actor_id); return self._save(s)
    def reject(self,c): s=self._get(c.scenario_id); s.reject(c.actor_id); return self._save(s)
    def archive(self,c): s=self._get(c.scenario_id); s.archive(c.actor_id); return self._save(s)
    def update(self,c):
        s=self._get(c.scenario_id); changes={k:v for k,v in {'name':c.name,'description':c.description,'scenario_type':c.scenario_type,'source':c.source,'probability':c.probability,'confidence':c.confidence}.items() if v is not None}; s.update(c.actor_id,**changes); self.uow.policy.ensure_unique_name(self.uow.repository,s); return self._save(s)
