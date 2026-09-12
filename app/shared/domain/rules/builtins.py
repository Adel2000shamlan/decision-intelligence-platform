from dataclasses import dataclass
from app.shared.domain.rules.engine import RuleContext, RuleResult

@dataclass(frozen=True)
class AlwaysValidRule:
    code: str = "RULE_VALID"
    def check(self, target, context: RuleContext) -> RuleResult:
        return RuleResult(self.code, "rule passed", True)
