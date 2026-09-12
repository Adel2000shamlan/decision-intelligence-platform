from dataclasses import dataclass
from app.shared.domain.rules import RuleContext, RuleResult, RuleSet
from .models import Scenario, ScenarioStatus

@dataclass(frozen=True)
class ScenarioIdentityRule:
    code: str = 'SCENARIO_IDENTITY'
    def check(self, target: Scenario, context: RuleContext) -> RuleResult:
        ok = target.decision_id is not None and target.option_id is not None and bool(target.name.strip())
        return RuleResult(self.code, 'scenario identity and name are valid', ok)

@dataclass(frozen=True)
class ScenarioProbabilityRule:
    code: str = 'SCENARIO_PROBABILITY_CONFIDENCE'
    def check(self, target: Scenario, context: RuleContext) -> RuleResult:
        p = target.probability is None or 0 <= target.probability <= 100
        c = target.confidence is None or 0 <= target.confidence <= 100
        return RuleResult(self.code, 'probability and confidence are within 0..100', p and c)

@dataclass(frozen=True)
class ScenarioLifecycleRule:
    code: str = 'SCENARIO_LIFECYCLE'
    def check(self, target: Scenario, context: RuleContext) -> RuleResult:
        return RuleResult(self.code, 'scenario status is valid', isinstance(target.status, ScenarioStatus))

RULES = RuleSet((ScenarioIdentityRule(), ScenarioProbabilityRule(), ScenarioLifecycleRule()))
