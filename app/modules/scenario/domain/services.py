from __future__ import annotations
from uuid import UUID
from app.shared.domain.services import DomainServiceBase, ServiceResult
from app.shared.domain.errors import BusinessRuleViolation
from .models import Scenario, ScenarioStatus

class ScenarioDomainService(DomainServiceBase):
    def create(self, repository, decision_repository, option_repository, decision_id: UUID, option_id: UUID, name: str, description='', scenario_type='custom', source='human', probability=None, confidence=None, actor_id=None) -> ServiceResult[Scenario]:
        decision=self.require(decision_repository.get_by_id(decision_id),'decision',decision_id)
        option=self.require(option_repository.get_by_id(option_id),'option',option_id)
        if option.decision_id != decision.id: raise BusinessRuleViolation('option does not belong to decision')
        scenario=Scenario.create(decision_id,option_id,name,description,scenario_type,source,probability,confidence,actor_id)
        self.ensure_unique_name(repository,scenario); repository.save(scenario); return self.collect(scenario)
    def start_analysis(self,repository,scenario_id,actor_id=None,expected_version=None): return self._invoke(repository,scenario_id,'start_analysis',actor_id,expected_version)
    def evaluate(self,repository,scenario_id,actor_id=None,expected_version=None): return self._invoke(repository,scenario_id,'evaluate',actor_id,expected_version)
    def approve(self,repository,scenario_id,actor_id=None,expected_version=None): return self._invoke(repository,scenario_id,'approve',actor_id,expected_version)
    def reject(self,repository,scenario_id,actor_id=None,expected_version=None): return self._invoke(repository,scenario_id,'reject',actor_id,expected_version)
    def archive(self,repository,scenario_id,actor_id=None,expected_version=None): return self._invoke(repository,scenario_id,'archive',actor_id,expected_version)
    def update(self,repository,scenario_id,actor_id=None,expected_version=None,**changes):
        s=self._get(repository,scenario_id,expected_version); s.update(actor_id,**changes); repository.save(s); return self.collect(s)
    def ensure_unique_name(self,repository,scenario):
        if repository.exists_by_name(scenario.decision_id,scenario.name): raise BusinessRuleViolation(f'scenario name already exists in decision: {scenario.name}')
    def _get(self,repository,scenario_id,expected_version=None):
        s=self.require(repository.get_by_id(scenario_id),'scenario',scenario_id); self.ensure_version(s,expected_version); return s
    def _invoke(self,repository,scenario_id,method,actor_id,expected_version):
        s=self._get(repository,scenario_id,expected_version); getattr(s,method)(actor_id); repository.save(s); return self.collect(s)

class ScenarioPolicyService:
    def ensure_unique_name(self,repository,scenario): ScenarioDomainService().ensure_unique_name(repository,scenario)
    def ensure_can_start_analysis(self,scenario):
        if scenario.status is not ScenarioStatus.DRAFT: raise BusinessRuleViolation('only draft scenarios can start analysis')
    def ensure_can_evaluate(self,scenario):
        if scenario.status is not ScenarioStatus.UNDER_ANALYSIS: raise BusinessRuleViolation('only scenarios under analysis can be evaluated')
    def ensure_can_approve(self,scenario,actor_id):
        if scenario.status is not ScenarioStatus.EVALUATED: raise BusinessRuleViolation('only evaluated scenarios can be approved')
        if actor_id is None: raise BusinessRuleViolation('scenario approval requires an explicit human actor_id')
