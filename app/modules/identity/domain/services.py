from uuid import UUID
from app.shared.domain.errors import BusinessRuleViolation, EntityNotFound
from app.shared.domain.services import DomainServiceBase, ServiceResult
from .models import User
from .rules import USER_RULE_SET
from app.shared.domain.rules.engine import RuleContext
class UserLifecycleService(DomainServiceBase):
    def create(self,repository,email,display_name,description='',actor_id=None):
        user=User.create(email,display_name,description,actor_id)
        if repository.exists_by_email(user.email_address): raise BusinessRuleViolation('user email already exists')
        repository.save(user); return self.collect(user)
    def suspend(self,repository,user_id,actor_id=None,reason='',expected_version=None): return self._invoke(repository,user_id,'suspend',actor_id,expected_version,reason)
    def reactivate(self,repository,user_id,actor_id=None,expected_version=None): return self._invoke(repository,user_id,'reactivate',actor_id,expected_version)
    def archive(self,repository,user_id,actor_id=None,reason='',expected_version=None): return self._invoke(repository,user_id,'archive',actor_id,expected_version,reason)
    def rename(self,repository,user_id,new_name,actor_id=None,expected_version=None):
        user=self._get(repository,user_id,expected_version); user.rename(new_name,actor_id); repository.save(user); return self.collect(user)
    def _get(self,repository,user_id,expected_version=None):
        user=self.require(repository.get_by_id(user_id),'user',user_id); self.ensure_version(user,expected_version); return user
    def _invoke(self,repository,user_id,method,actor_id,expected_version,*args):
        user=self._get(repository,user_id,expected_version); USER_RULE_SET.assert_valid(user, RuleContext(operation=method, actor_id=actor_id)); getattr(user,method)(actor_id,*args); repository.save(user); return self.collect(user)
