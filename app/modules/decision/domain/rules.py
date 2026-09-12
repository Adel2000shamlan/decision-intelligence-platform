from dataclasses import dataclass
from app.shared.domain.rules import RuleContext, RuleResult, RuleSet
from .models import Decision, DecisionStatus

@dataclass(frozen=True)
class DecisionIdentityRule:
    code: str = 'DECISION_IDENTITY'
    def check(self, target: Decision, context: RuleContext) -> RuleResult:
        ok = target.organization_id is not None and target.project_id is not None and bool(target.title.strip())
        return RuleResult(self.code, 'decision identity and title are valid', ok)

@dataclass(frozen=True)
class DecisionLifecycleRule:
    code: str = 'DECISION_LIFECYCLE'
    def check(self, target: Decision, context: RuleContext) -> RuleResult:
        ok = isinstance(target.status, DecisionStatus)
        return RuleResult(self.code, 'decision status is valid', ok)

@dataclass(frozen=True)
class DecisionApprovalActorRule:
    code: str = 'DECISION_APPROVAL_ACTOR'
    def check(self, target: Decision, context: RuleContext) -> RuleResult:
        if context.operation in ('approve', 'reject') and context.actor_id is None:
            return RuleResult(self.code, 'human actor is required for approval decisions', False)
        return RuleResult(self.code, 'approval actor requirement satisfied', True)

RULES = RuleSet((DecisionIdentityRule(), DecisionLifecycleRule(), DecisionApprovalActorRule()))
