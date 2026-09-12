from uuid import UUID
from app.shared.domain.errors import EntityNotFound
from app.modules.organization.domain.models import Organization
from app.modules.organization.domain.services import OrganizationDomainService

class OrganizationApplicationService:
    def __init__(self, repository, event_publisher=None, audit_sink=None, authorization=None):
        self.repository=repository; self.domain=OrganizationDomainService(); self.event_publisher=event_publisher; self.audit_sink=audit_sink; self.authorization=authorization
    def _guard(self, action, actor_id, tenant_id=None, resource_id=None):
        if self.authorization: self.authorization.require(action=action, actor_id=actor_id, tenant_id=tenant_id, resource_id=resource_id)
    def create(self, name, slug, actor_id=None, tenant_id=None):
        self._guard('create',actor_id,tenant_id); result=self.domain.create(self.repository,name,slug,actor_id); self._post(result.entity,actor_id,'create'); return result.entity
    def get(self, organization_id):
        item=self.repository.get_by_id(organization_id)
        if item is None: raise EntityNotFound(f'organization not found: {organization_id}')
        return item
    def list(self, tenant_id=None): return self.repository.list(tenant_id)
    def rename(self, organization_id, new_name, actor_id=None, tenant_id=None):
        self._guard('update',actor_id,tenant_id,organization_id); result=self.domain.rename(self.repository,organization_id,new_name,actor_id); self._post(result.entity,actor_id,'update'); return result.entity
    def suspend(self, organization_id, actor_id=None, tenant_id=None):
        self._guard('update',actor_id,tenant_id,organization_id); result=self.domain.suspend(self.repository,organization_id,actor_id); self._post(result.entity,actor_id,'update'); return result.entity
    def reactivate(self, organization_id, actor_id=None, tenant_id=None):
        self._guard('update',actor_id,tenant_id,organization_id); result=self.domain.reactivate(self.repository,organization_id,actor_id); self._post(result.entity,actor_id,'update'); return result.entity
    def archive(self, organization_id, actor_id=None, tenant_id=None):
        self._guard('archive',actor_id,tenant_id,organization_id); result=self.domain.archive(self.repository,organization_id,actor_id); self._post(result.entity,actor_id,'archive'); return result.entity
    def _post(self, entity, actor_id, action):
        events=entity.pull_events()
        if self.event_publisher:
            for event in events: self.event_publisher.publish(event)
        if self.audit_sink: self.audit_sink.record(entity.id,actor_id,action,entity.version)
