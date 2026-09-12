from __future__ import annotations
from app.shared.domain.services import DomainService, ServiceResult
from .models import AuthorizationContext, PolicyDecision
from .resource_authorization import ResourceAuthorizationEngine, ResourceResolver


class ResourceAuthorizationService(DomainService):
    """Resource-scoped authorization facade. It never grants a permission by itself."""
    def __init__(self, resolver: ResourceResolver) -> None:
        self._engine = ResourceAuthorizationEngine(resolver)

    def authorize(self, context: AuthorizationContext) -> ServiceResult[PolicyDecision]:
        return ServiceResult(self._engine.evaluate(context))

    def require(self, context: AuthorizationContext) -> PolicyDecision:
        decision = self._engine.evaluate(context)
        if not decision.allowed:
            from .models import AuthorizationError
            raise AuthorizationError(decision.reason)
        return decision
