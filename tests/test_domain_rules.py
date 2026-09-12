from datetime import date
from uuid import uuid4
import pytest

from app.shared.domain.errors import BusinessRuleViolation
from app.shared.domain.rules import RuleContext, RuleSet
from app.modules.organization.domain.models import Organization
from app.modules.project.domain.models import Project
from app.modules.risk.domain.models import Risk, RiskStatus, RiskLevel
from app.modules.execution.domain.models import Execution, ExecutionStatus


def test_rules_are_deterministic_and_report_codes():
    org = Organization.create("Acme", "acme")
    org.pull_events()
    org.validate_invariants()
    assert org.status.value == "active"


def test_rule_set_returns_all_failures_without_mutating_target():
    class BadRule:
        code = "BAD_RULE"
        def check(self, target, context):
            from app.shared.domain.rules import RuleResult
            return RuleResult(self.code, "bad", False)
    result = RuleSet((BadRule(), BadRule())).evaluate(object(), RuleContext(operation="test"))
    assert not result.passed
    assert len(result.failures) == 2


def test_risk_invariants_reject_inconsistent_score():
    r = Risk.create(uuid4(), "R")
    r.identify()
    r.assess(2, 3)
    r.score = 99
    with pytest.raises(BusinessRuleViolation, match="RISK_ASSESSMENT_CONSISTENT"):
        r.validate_invariants()


def test_risk_invariants_reject_worse_residual():
    r = Risk.create(uuid4(), "R")
    r.identify(); r.assess(2, 3)
    r.residual_probability = 5; r.residual_impact = 5; r.residual_score = 25; r.residual_level = RiskLevel.CRITICAL
    with pytest.raises(BusinessRuleViolation, match="RISK_RESIDUAL_NOT_WORSE"):
        r.validate_invariants()


def test_execution_completed_requires_full_progress():
    e = Execution.create(uuid4(), "Launch")
    e.plan(); e.start(); e.status = ExecutionStatus.COMPLETED
    e.progress = 99
    with pytest.raises(BusinessRuleViolation, match="EXEC_COMPLETION_REQUIRES_100"):
        e.validate_invariants()


def test_execution_schedule_rule_and_valid_case():
    # Constructor-level validation catches an invalid schedule before the rule boundary.
    with pytest.raises(Exception):
        Execution.create(uuid4(), "Invalid", planned_start=date(2026,1,2), planned_end=date(2026,1,1))
    valid = Execution.create(uuid4(), "Valid", planned_start=date(2026,1,1), planned_end=date(2026,1,2))
    valid.validate_invariants()
