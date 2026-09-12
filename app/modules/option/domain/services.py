from __future__ import annotations
from uuid import UUID
from app.shared.domain.services import DomainServiceBase, ServiceResult
from app.shared.domain.errors import BusinessRuleViolation
from .models import Option, OptionStatus, OptionSource, OptionType

class OptionDomainService(DomainServiceBase):
    def create(self, repository, decision_repository, decision_id: UUID, title: str, description='', option_type='original', source='human', rank=None, actor_id=None) -> ServiceResult[Option]:
        self.require(decision_repository.get_by_id(decision_id), 'decision', decision_id)
        option=Option.create(decision_id,title,description,option_type,source,rank,actor_id)
        self.ensure_unique_title(repository,option); self.ensure_ai_option_is_alternative(option)
        repository.save(option); return self.collect(option)
    def start_evaluation(self, repository, option_id, actor_id=None, expected_version=None): return self._invoke(repository,option_id,'start_evaluation',actor_id,expected_version)
    def mark_eligible(self, repository, option_id, actor_id=None, expected_version=None): return self._invoke(repository,option_id,'mark_eligible',actor_id,expected_version)
    def select(self, repository, option_id, actor_id=None, expected_version=None): return self._invoke(repository,option_id,'select',actor_id,expected_version)
    def reject(self, repository, option_id, actor_id=None, expected_version=None): return self._invoke(repository,option_id,'reject',actor_id,expected_version)
    def withdraw(self, repository, option_id, actor_id=None, expected_version=None): return self._invoke(repository,option_id,'withdraw',actor_id,expected_version)
    def archive(self, repository, option_id, actor_id=None, expected_version=None): return self._invoke(repository,option_id,'archive',actor_id,expected_version)
    def update(self, repository, option_id, actor_id=None, expected_version=None, **changes):
        o=self._get(repository,option_id,expected_version); o.update(actor_id,**changes); repository.save(o); return self.collect(o)
    def ensure_unique_title(self,repository,option):
        if repository.exists_by_title(option.decision_id,option.title): raise BusinessRuleViolation(f'option title already exists in decision: {option.title}')
    def ensure_ai_option_is_alternative(self,option):
        if option.source is OptionSource.AI and option.option_type is not OptionType.ALTERNATIVE: raise BusinessRuleViolation('AI-generated options must be marked as alternative')
    def _get(self,repository,option_id,expected_version=None):
        o=self.require(repository.get_by_id(option_id),'option',option_id); self.ensure_version(o,expected_version); return o
    def _invoke(self,repository,option_id,method,actor_id,expected_version):
        o=self._get(repository,option_id,expected_version); getattr(o,method)(actor_id); repository.save(o); return self.collect(o)

class OptionPolicyService:
    def ensure_unique_title(self,repository,option): OptionDomainService().ensure_unique_title(repository,option)
    def ensure_can_start_evaluation(self,option):
        if option.status is not OptionStatus.DRAFT: raise BusinessRuleViolation('only draft options can start evaluation')
    def ensure_can_mark_eligible(self,option):
        if option.status is not OptionStatus.UNDER_EVALUATION: raise BusinessRuleViolation('only options under evaluation can become eligible')
    def ensure_can_select(self,option):
        if option.status is not OptionStatus.ELIGIBLE: raise BusinessRuleViolation('only eligible options can be selected')
    def ensure_ai_option_is_alternative(self,option): OptionDomainService().ensure_ai_option_is_alternative(option)
