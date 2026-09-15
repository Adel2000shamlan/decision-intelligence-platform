from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.modules.authorization.domain.human_approval import (
    HumanApprovalAuthorizationService,
)
from app.modules.authorization.domain.models import AuthorizationContext


@dataclass(frozen=True, slots=True)
class HumanApprovalGateResult:
    approved: bool
    policy_id: str
    reason: str
    correlation_id: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.approved, bool):
            raise ValueError("approved must be bool")

        if not isinstance(self.policy_id, str) or not self.policy_id.strip():
            raise ValueError("policy_id is required")

        if not isinstance(self.reason, str) or not self.reason.strip():
            raise ValueError("reason is required")

        if not isinstance(self.correlation_id, UUID):
            raise ValueError("correlation_id must be UUID")


class HumanApprovalGate:
    """Adapter over the existing authorization human-approval boundary."""

    def __init__(
        self,
        authorization: HumanApprovalAuthorizationService | None = None,
    ) -> None:
        self.authorization = authorization or HumanApprovalAuthorizationService()

    def evaluate(
        self,
        context: AuthorizationContext,
    ) -> HumanApprovalGateResult:
        decision = self.authorization.authorize(context)

        return HumanApprovalGateResult(
            approved=decision.allowed,
            policy_id=decision.policy_id,
            reason=decision.reason,
            correlation_id=decision.correlation_id,
        )

    def require(
        self,
        context: AuthorizationContext,
    ) -> HumanApprovalGateResult:
        result = self.evaluate(context)

        if not result.approved:
            self.authorization.require(context)

        return result
