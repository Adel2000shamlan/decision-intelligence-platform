from __future__ import annotations
from uuid import UUID
from app.shared.domain.services import DomainServiceBase, ServiceResult
from app.shared.domain.errors import BusinessRuleViolation
from .models import Risk, RiskStatus, RiskSource

class RiskDomainService(DomainServiceBase):
    def create(self, repository, project_id: UUID, title: str, description: str = '', decision_id: UUID | None = None, source: RiskSource = RiskSource.HUMAN, actor_id: UUID | None = None) -> ServiceResult[Risk]:
        risk = Risk.create(project_id, title, description, decision_id, source, actor_id)
        self.ensure_unique_title(repository, risk); repository.save(risk); return self.collect(risk)
    def identify(self, repository, risk_id, actor_id=None, expected_version=None): return self._invoke(repository, risk_id, 'identify', actor_id, expected_version)
    def assess(self, repository, risk_id, probability, impact, actor_id=None, expected_version=None):
        risk = self._get(repository, risk_id, expected_version); risk.assess(probability, impact, actor_id); repository.save(risk); return self.collect(risk)
    def start_mitigation(self, repository, risk_id, actor_id=None, expected_version=None): return self._invoke(repository, risk_id, 'start_mitigation', actor_id, expected_version)
    def monitor(self, repository, risk_id, residual_probability, residual_impact, actor_id=None, expected_version=None):
        risk = self._get(repository, risk_id, expected_version)
        risk.ensure_assessed(); prospective = residual_probability * residual_impact
        if prospective > risk.score: raise BusinessRuleViolation('residual risk cannot exceed inherent risk without explicit override')
        risk.monitor(residual_probability, residual_impact, actor_id); repository.save(risk); return self.collect(risk)
    def accept(self, repository, risk_id, actor_id=None, expected_version=None): return self._invoke(repository, risk_id, 'accept', actor_id, expected_version)
    def close(self, repository, risk_id, actor_id=None, expected_version=None): return self._invoke(repository, risk_id, 'close', actor_id, expected_version)
    def archive(self, repository, risk_id, actor_id=None, expected_version=None): return self._invoke(repository, risk_id, 'archive', actor_id, expected_version)
    def rename(self, repository, risk_id, new_title, actor_id=None, expected_version=None):
        risk=self._get(repository,risk_id,expected_version)
        if risk.status is RiskStatus.ARCHIVED: raise BusinessRuleViolation('archived risk cannot be renamed')
        if repository.exists_by_title(risk.project_id,new_title.strip()) and new_title.strip()!=risk.title: raise BusinessRuleViolation('risk title already exists in project')
        risk.rename(new_title,actor_id); repository.save(risk); return self.collect(risk)
    def ensure_unique_title(self, repository, risk):
        if repository.exists_by_title(risk.project_id,risk.title): raise BusinessRuleViolation(f'risk title already exists in project: {risk.title}')
    def _get(self, repository, risk_id, expected_version=None):
        risk=self.require(repository.get_by_id(risk_id),'risk',risk_id); self.ensure_version(risk,expected_version); return risk
    def _invoke(self, repository, risk_id, method, actor_id, expected_version):
        risk=self._get(repository,risk_id,expected_version); getattr(risk,method)(actor_id); repository.save(risk); return self.collect(risk)

class RiskPolicyService:
    def ensure_unique_title(self,repository,risk:Risk): RiskDomainService().ensure_unique_title(repository,risk)
    def ensure_can_assess(self,risk:Risk):
        if risk.status is not RiskStatus.IDENTIFIED: raise BusinessRuleViolation('only identified risks can be assessed')
    def ensure_can_select_mitigation(self,risk:Risk):
        if risk.status not in (RiskStatus.ASSESSED,RiskStatus.MONITORED,RiskStatus.MITIGATING): raise BusinessRuleViolation('risk is not eligible for mitigation')
    def ensure_residual_not_worse(self,risk:Risk):
        if risk.score is not None and risk.residual_score is not None and risk.residual_score>risk.score: raise BusinessRuleViolation('residual risk cannot exceed inherent risk without explicit override')
