from dataclasses import dataclass
from app.shared.domain.rules import RuleContext, RuleResult, RuleSet
from .models import Execution, ExecutionStatus

@dataclass(frozen=True)
class ExecutionProgressRule:
    code: str = "EXEC_PROGRESS_BOUNDS"
    def check(self, e: Execution, context: RuleContext) -> RuleResult:
        ok = 0 <= e.progress <= 100 and e.resources_consumed >= 0 and e.budget_spent >= 0
        return RuleResult(self.code, "progress must be 0..100 and consumption values must be non-negative", ok)

@dataclass(frozen=True)
class ExecutionCompletionRule:
    code: str = "EXEC_COMPLETION_REQUIRES_100"
    def check(self, e: Execution, context: RuleContext) -> RuleResult:
        ok = e.status != ExecutionStatus.COMPLETED or e.progress == 100
        return RuleResult(self.code, "completed execution must have 100% progress", ok)

@dataclass(frozen=True)
class ExecutionScheduleRule:
    code: str = "EXEC_SCHEDULE_VALID"
    def check(self, e: Execution, context: RuleContext) -> RuleResult:
        ok = not (e.planned_start and e.planned_end) or e.planned_end >= e.planned_start
        return RuleResult(self.code, "planned end cannot precede planned start", ok)

@dataclass(frozen=True)
class ExecutionCollectionRule:
    code: str = "EXEC_COLLECTIONS_VALID"
    def check(self, e: Execution, context: RuleContext) -> RuleResult:
        ok = all(t.weight >= 0 and 0 <= t.progress <= 100 for t in e.tasks) and all(0 <= m.progress <= 100 for m in e.milestones)
        return RuleResult(self.code, "task and milestone progress must be within bounds", ok)

RULES = RuleSet((ExecutionProgressRule(), ExecutionCompletionRule(), ExecutionScheduleRule(), ExecutionCollectionRule()))
