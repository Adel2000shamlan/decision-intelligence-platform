from dataclasses import dataclass
from app.shared.domain.rules import RuleContext, RuleResult, RuleSet
from .models import Project, ProjectStatus

@dataclass(frozen=True)
class ProjectIdentityRule:
    code: str = "PROJECT_IDENTITY_VALID"
    def check(self, p: Project, context: RuleContext) -> RuleResult:
        ok = p.organization_id is not None and isinstance(p.name, str) and bool(p.name.strip()) and len(p.name) <= 200
        return RuleResult(self.code, "project organization and name are required", ok)

@dataclass(frozen=True)
class ProjectLifecycleRule:
    code: str = "PROJECT_STATUS_VALID"
    def check(self, p: Project, context: RuleContext) -> RuleResult:
        ok = isinstance(p.status, ProjectStatus)
        return RuleResult(self.code, "project must have a valid lifecycle status", ok)

RULES = RuleSet((ProjectIdentityRule(), ProjectLifecycleRule()))
