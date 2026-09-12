from uuid import UUID
class ProjectAuthorizationError(PermissionError): pass
class ProjectAuthorizationAdapter:
    def __init__(self, allowed=None): self.allowed=set(allowed or ())
    def require(self, action, actor_id, tenant_id, resource_id=None):
        if actor_id is None: raise ProjectAuthorizationError('authenticated actor required')
        key=f'project:{action}'
        if self.allowed and key not in self.allowed: raise ProjectAuthorizationError(f'permission denied: {key}')
        if tenant_id is None: raise ProjectAuthorizationError('tenant context required')
