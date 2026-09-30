class BusinessAssessmentAuthorizationError(PermissionError):
    pass


class BusinessAssessmentAuthorizationAdapter:
    def __init__(self, allowed=None):
        self.allowed = set(allowed or ())

    def require(
        self,
        action,
        actor_id,
        tenant_id,
        resource_id=None,
    ):
        if actor_id is None:
            raise BusinessAssessmentAuthorizationError(
                "authenticated actor required"
            )

        key = f"business_assessment:{action}"

        if self.allowed and key not in self.allowed:
            raise BusinessAssessmentAuthorizationError(
                f"permission denied: {key}"
            )

        if tenant_id is None:
            raise BusinessAssessmentAuthorizationError(
                "tenant context required"
            )
