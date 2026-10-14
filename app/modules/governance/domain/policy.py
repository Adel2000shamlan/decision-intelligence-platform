from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class GovernanceContext:
    tenant_id: UUID
    actor_id: UUID | None
    permission: str
    resource: str
    correlation_id: UUID


@dataclass(frozen=True, slots=True)
class GovernanceDecision:
    allowed: bool
    reason: str
    policy_id: str
    tenant_id: UUID
    correlation_id: UUID


@dataclass(frozen=True, slots=True)
class DefaultDenyPolicy:
    policy_id: str = "governance.default-deny.v1"

    def evaluate(self, context: GovernanceContext) -> GovernanceDecision:
        return GovernanceDecision(
            allowed=False,
            reason="governance policy denied by default",
            policy_id=self.policy_id,
            tenant_id=context.tenant_id,
            correlation_id=context.correlation_id,
        )


@dataclass(frozen=True, slots=True)
class GovernancePolicy:
    """
    Deterministic governance gate.

    Security invariant:
    - authorization is denied unless an explicit rule allows it;
    - tenant identity must always be present;
    - correlation identity must always be present;
    - governance never grants permission implicitly.
    """

    policy_id: str = "governance.policy.v1"
    default_deny: DefaultDenyPolicy = DefaultDenyPolicy()
    fail_closed: bool = True

    def evaluate(self, context: GovernanceContext) -> GovernanceDecision:
        if not self.fail_closed:
            raise ValueError("governance policy must be fail-closed")

        if not isinstance(context.tenant_id, UUID):
            return GovernanceDecision(
                False,
                "tenant context is required",
                self.policy_id,
                context.tenant_id,
                context.correlation_id,
            )

        if not isinstance(context.correlation_id, UUID):
            return GovernanceDecision(
                False,
                "correlation context is required",
                self.policy_id,
                context.tenant_id,
                context.correlation_id,
            )

        return self.default_deny.evaluate(context)

    def require(self, context: GovernanceContext) -> GovernanceDecision:
        decision = self.evaluate(context)
        if not decision.allowed:
            raise PermissionError(decision.reason)
        return decision
