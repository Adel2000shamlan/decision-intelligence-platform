from __future__ import annotations
from uuid import UUID
from app.shared.domain.services import DomainServiceBase, ServiceResult
from app.shared.domain.errors import BusinessRuleViolation
from .models import Execution

class ExecutionDomainService(DomainServiceBase):
    def create(self, repository, project_id: UUID, title: str, description: str = '', planned_start=None, planned_end=None, budget=0, resource_plan=0, actor_id=None) -> ServiceResult[Execution]:
        execution=Execution.create(project_id,title,description,planned_start,planned_end,budget,resource_plan,actor_id)
        self.ensure_unique_title(repository,execution); repository.save(execution); return self.collect(execution)
    def plan(self, repository, execution_id, actor_id=None, expected_version=None): return self._invoke(repository,execution_id,'plan',actor_id,expected_version)
    def start(self, repository, execution_id, actor_id=None, expected_version=None): return self._invoke(repository,execution_id,'start',actor_id,expected_version)
    def mark_at_risk(self, repository, execution_id, actor_id=None, expected_version=None): return self._invoke(repository,execution_id,'mark_at_risk',actor_id,expected_version)
    def block(self, repository, execution_id, actor_id=None, expected_version=None): return self._invoke(repository,execution_id,'block',actor_id,expected_version)
    def complete(self, repository, execution_id, actor_id=None, expected_version=None): return self._invoke(repository,execution_id,'complete',actor_id,expected_version)
    def cancel(self, repository, execution_id, actor_id=None, expected_version=None): return self._invoke(repository,execution_id,'cancel',actor_id,expected_version)
    def archive(self, repository, execution_id, actor_id=None, expected_version=None): return self._invoke(repository,execution_id,'archive',actor_id,expected_version)
    def update_progress(self, repository, execution_id, progress, actor_id=None, expected_version=None): return self._invoke(repository,execution_id,'update_progress',actor_id,expected_version,progress)
    def record_budget_spend(self, repository, execution_id, amount, actor_id=None, expected_version=None): return self._invoke(repository,execution_id,'record_budget_spend',actor_id,expected_version,amount)
    def record_resource_consumption(self, repository, execution_id, amount, actor_id=None, expected_version=None): return self._invoke(repository,execution_id,'record_resource_consumption',actor_id,expected_version,amount)
    def record_schedule_variance(self, repository, execution_id, days, actor_id=None, expected_version=None): return self._invoke(repository,execution_id,'record_schedule_variance',actor_id,expected_version,days)
    def calculate_health(self, repository, execution_id, actor_id=None, expected_version=None): return self._invoke(repository,execution_id,'calculate_health',actor_id,expected_version)
    def rename(self, repository, execution_id, new_title, actor_id=None, expected_version=None):
        e=self._get(repository,execution_id,expected_version)
        if e.status.value=='archived': raise BusinessRuleViolation('archived execution cannot be renamed')
        if repository.exists_by_title(e.project_id,new_title.strip(),e.id): raise BusinessRuleViolation('execution title must be unique within project')
        e.rename(new_title,actor_id); repository.save(e); return self.collect(e)
    def ensure_unique_title(self,repository,execution):
        if repository.exists_by_title(execution.project_id,execution.title,None): raise BusinessRuleViolation('execution title must be unique within project')
    def _get(self,repository,execution_id,expected_version=None):
        e=self.require(repository.get_by_id(execution_id),'execution',execution_id); self.ensure_version(e,expected_version); return e
    def _invoke(self,repository,execution_id,method,actor_id,expected_version,*args):
        e=self._get(repository,execution_id,expected_version); getattr(e,method)(*args,actor_id=actor_id); repository.save(e); return self.collect(e)

class ExecutionPolicyService:
    def ensure_unique_title(self,repo,project_id,title,exclude_id=None):
        if repo.exists_by_title(project_id,title,exclude_id): raise BusinessRuleViolation('execution title must be unique within project')
    def can_record(self,execution):
        if execution.status.value in ('completed','cancelled','archived'): raise BusinessRuleViolation('execution is not mutable in its current state')
