from dataclasses import dataclass
from app.shared.domain.rules import RuleContext, RuleResult, RuleSet
from .models import Option, OptionSource, OptionType, OptionStatus

@dataclass(frozen=True)
class OptionIdentityRule:
    code: str = 'OPTION_IDENTITY'
    def check(self, target: Option, context: RuleContext) -> RuleResult:
        ok = target.decision_id is not None and bool(target.title.strip())
        return RuleResult(self.code, 'option identity and title are valid', ok)

@dataclass(frozen=True)
class OptionAiGovernanceRule:
    code: str = 'OPTION_AI_ALTERNATIVE'
    def check(self, target: Option, context: RuleContext) -> RuleResult:
        ok = target.source is not OptionSource.AI or target.option_type is OptionType.ALTERNATIVE
        return RuleResult(self.code, 'AI-sourced options must be alternatives', ok)

@dataclass(frozen=True)
class OptionLifecycleRule:
    code: str = 'OPTION_LIFECYCLE'
    def check(self, target: Option, context: RuleContext) -> RuleResult:
        return RuleResult(self.code, 'option status is valid', isinstance(target.status, OptionStatus))

RULES = RuleSet((OptionIdentityRule(), OptionAiGovernanceRule(), OptionLifecycleRule()))
