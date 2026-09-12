from __future__ import annotations
from typing import Protocol
from app.modules.authorization.domain.models import AuthorizationContext, PolicyDecision

class AuthorizationEvaluatorPort(Protocol):
    def authorize(self, context: AuthorizationContext) -> PolicyDecision: ...
