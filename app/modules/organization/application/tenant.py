from uuid import UUID
from app.shared.domain.errors import BusinessRuleViolation
class OrganizationTenantGuard:
    def require(self, organization, tenant_id):
        actual=getattr(organization,'tenant_id',None)
        if actual is not None and str(actual)!=str(tenant_id): raise BusinessRuleViolation('organization tenant mismatch')
        return True
