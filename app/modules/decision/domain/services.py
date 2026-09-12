from __future__ import annotations
from uuid import UUID
from app.shared.domain.services import DomainServiceBase, ServiceResult
from app.shared.domain.errors import BusinessRuleViolation
from .models import Decision, DecisionStatus

class DecisionDomainService(DomainServiceBase):
    def create(self, repository, organization_id: UUID, project_id: UUID, title: str, description='', decision_type='strategic', priority='medium', actor_id=None) -> ServiceResult[Decision]:
        decision = Decision.create(organization_id, project_id, title, description, decision_type, priority, actor_id)
        self.ensure_unique_title(repository, decision)
        repository.save(decision)
        return self.collect(decision)
    def start_analysis(self, repository, decision_id, actor_id=None, expected_version=None): return self._invoke(repository, decision_id, 'start_analysis', actor_id, expected_version)
    def submit_for_approval(self, repository, decision_id, actor_id=None, expected_version=None): return self._invoke(repository, decision_id, 'submit_for_approval', actor_id, expected_version)
    def approve(self, repository, decision_id, actor_id=None, expected_version=None): return self._invoke(repository, decision_id, 'approve', actor_id, expected_version)
    def reject(self, repository, decision_id, reason=None, actor_id=None, expected_version=None):
        d=self._get(repository, decision_id, expected_version); d.reject(reason, actor_id); repository.save(d); return self.collect(d)
    def cancel(self, repository, decision_id, reason=None, actor_id=None, expected_version=None):
        d=self._get(repository, decision_id, expected_version); d.cancel(reason, actor_id); repository.save(d); return self.collect(d)
    def execute(self, repository, decision_id, actor_id=None, expected_version=None): return self._invoke(repository, decision_id, 'execute', actor_id, expected_version)
    def close(self, repository, decision_id, actor_id=None, expected_version=None): return self._invoke(repository, decision_id, 'close', actor_id, expected_version)
    def update(self, repository, decision_id, field_name, value, actor_id=None, expected_version=None):
        d=self._get(repository, decision_id, expected_version); d.update(field_name, value, actor_id); repository.save(d); return self.collect(d)
    def ensure_unique_title(self, repository, decision):
        if repository.exists_by_title(decision.project_id, decision.title):
            raise BusinessRuleViolation(f'decision title already exists in project: {decision.title}')
    def _get(self, repository, decision_id, expected_version=None):
        d=self.require(repository.get_by_id(decision_id), 'decision', decision_id); self.ensure_version(d, expected_version); return d
    def _invoke(self, repository, decision_id, method, actor_id, expected_version):
        d=self._get(repository, decision_id, expected_version); getattr(d, method)(actor_id); repository.save(d); return self.collect(d)

class DecisionPolicyService:
    def ensure_unique_title(self, repository, decision): DecisionDomainService().ensure_unique_title(repository, decision)
    def ensure_can_submit(self, decision):
        if decision.status is not DecisionStatus.ANALYSIS: raise BusinessRuleViolation('only decisions in analysis can be submitted for approval')
    def ensure_can_approve(self, decision):
        if decision.status is not DecisionStatus.READY_FOR_APPROVAL: raise BusinessRuleViolation('only decisions ready for approval can be approved')
