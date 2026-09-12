from dataclasses import dataclass
from app.shared.domain.rules import RuleContext, RuleResult, RuleSet
from .models import Organization, OrganizationStatus

@dataclass(frozen=True)
class OrganizationNameRule:
    code: str = "ORG_NAME_REQUIRED"
    def check(self, o: Organization, context: RuleContext) -> RuleResult:
        ok = isinstance(o.name, str) and bool(o.name.strip()) and len(o.name) <= 200
        return RuleResult(self.code, "organization name must be non-empty and <= 200 characters", ok)

@dataclass(frozen=True)
class OrganizationSlugRule:
    code: str = "ORG_SLUG_VALID"
    def check(self, o: Organization, context: RuleContext) -> RuleResult:
        ok = isinstance(o.slug, str) and bool(o.slug) and o.slug == o.slug.lower() and len(o.slug) <= 100
        return RuleResult(self.code, "organization slug must be normalized lowercase and <= 100 characters", ok)

@dataclass(frozen=True)
class OrganizationLifecycleRule:
    code: str = "ORG_ARCHIVED_TERMINAL"
    def check(self, o: Organization, context: RuleContext) -> RuleResult:
        ok = o.status in OrganizationStatus
        return RuleResult(self.code, "organization must have a valid lifecycle status", ok)

RULES = RuleSet((OrganizationNameRule(), OrganizationSlugRule(), OrganizationLifecycleRule()))
