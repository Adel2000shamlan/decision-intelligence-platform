from uuid import UUID
from app.modules.organization.domain.models import Organization
from app.modules.organization.domain.repository import OrganizationRepository


class InMemoryOrganizationRepository(OrganizationRepository):
    def __init__(self): self._items: dict[UUID, Organization] = {}
    def get_by_id(self, organization_id): return self._items.get(organization_id)
    def get_by_slug(self, slug):
        slug = slug.strip().lower()
        return next((o for o in self._items.values() if o.slug == slug), None)
    def exists_by_slug(self, slug): return self.get_by_slug(slug) is not None
    def save(self, organization): self._items[organization.id] = organization; return organization


class DefaultOrganizationFactory:
    def create(self, name, slug, actor_id=None): return Organization.create(name, slug, actor_id)
