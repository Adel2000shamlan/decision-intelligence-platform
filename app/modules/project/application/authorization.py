from uuid import UUID


class ProjectAuthorizationError(PermissionError):
    pass


class ProjectAuthorizationAdapter:
    def __init__(self, allowed=None):
        self.allowed = set(allowed or ())

    def require(self, action, actor_id, tenant_id, resource_id=None):
        if actor_id is None:
            raise ProjectAuthorizationError(
                "authenticated actor required"
            )

        if tenant_id is None:
            raise ProjectAuthorizationError(
                "tenant context required"
            )

        key = f"project:{action}"
        if key not in self.allowed:
            raise ProjectAuthorizationError(
                f"permission denied: {key}"
            )
