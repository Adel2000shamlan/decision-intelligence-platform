from dataclasses import dataclass
from app.shared.domain.rules import RuleContext, RuleResult, RuleSet
from .models import Risk, RiskStatus, level_for

@dataclass(frozen=True)
class RiskAssessmentConsistencyRule:
    code: str = "RISK_ASSESSMENT_CONSISTENT"
    def check(self, r: Risk, context: RuleContext) -> RuleResult:
        complete = r.probability is not None and r.impact is not None and r.score is not None and r.level is not None
        if not complete:
            ok = r.status in (RiskStatus.DRAFT, RiskStatus.IDENTIFIED, RiskStatus.ARCHIVED)
            return RuleResult(self.code, "unassessed risks cannot carry partial assessment data", ok)
        ok = r.score == r.probability * r.impact and r.level == level_for(r.score)
        return RuleResult(self.code, "risk score and level must equal probability x impact", ok)

@dataclass(frozen=True)
class ResidualRiskRule:
    code: str = "RISK_RESIDUAL_NOT_WORSE"
    def check(self, r: Risk, context: RuleContext) -> RuleResult:
        if r.residual_score is None:
            return RuleResult(self.code, "no residual assessment present", True)
        ok = r.score is not None and r.residual_score <= r.score
        return RuleResult(self.code, "residual risk cannot exceed inherent risk", ok)

@dataclass(frozen=True)
class RiskStateDataRule:
    code: str = "RISK_STATE_DATA"
    def check(self, r: Risk, context: RuleContext) -> RuleResult:
        ok = r.status not in (RiskStatus.ASSESSED, RiskStatus.MITIGATING, RiskStatus.MONITORED, RiskStatus.ACCEPTED, RiskStatus.CLOSED) or r.score is not None
        return RuleResult(self.code, "assessed-or-later risk states require an assessment", ok)

RULES = RuleSet((RiskAssessmentConsistencyRule(), ResidualRiskRule(), RiskStateDataRule()))
