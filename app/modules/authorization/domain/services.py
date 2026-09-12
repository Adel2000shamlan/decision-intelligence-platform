from __future__ import annotations

from app.shared.domain.services import DomainService, ServiceResult
from .models import AuthorizationContext, AuthorizationPolicy, PolicyDecision
from .policy_engine import AuthorizationPolicyEngine
from .resource_authorization import ResourceResolver
from .authorization_services import AuthorizationServices


class AuthorizationService(DomainService):
    """Application-facing authorization facade backed by the deterministic policy engine."""

    def __init__(self, policies: tuple[AuthorizationPolicy, ...] = (), resource_resolver: ResourceResolver | None = None) -> None:
        self._policies = tuple(policies)
        self._engine = AuthorizationPolicyEngine(policies=self._policies, resource_resolver=resource_resolver)
        self._services = AuthorizationServices(self._engine)

    @property
    def policies(self) -> tuple[AuthorizationPolicy, ...]:
        return self._policies

    def authorize(self, context: AuthorizationContext) -> ServiceResult[PolicyDecision]:
        context.actor.require_authenticated()
        return ServiceResult(self._services.authorize(context))

    def require(self, context: AuthorizationContext) -> PolicyDecision:
        return self._services.require(context)
