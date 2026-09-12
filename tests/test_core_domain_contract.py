from uuid import uuid4
import importlib
import pytest

from app.shared.domain.aggregate import AggregateBoundary
from app.shared.domain.errors import BusinessRuleViolation, InvalidDomainData
from app.shared.domain.state_machines import (
    ORGANIZATION_STATE_MACHINE, PROJECT_STATE_MACHINE, RISK_STATE_MACHINE, EXECUTION_STATE_MACHINE,
)
from app.shared.domain.state_machine import validate_transition_graph
from app.modules.organization.domain.models import Organization, OrganizationStatus
from app.modules.project.domain.models import Project, ProjectStatus
from app.modules.risk.domain.models import Risk, RiskStatus, RiskLevel
from app.modules.execution.domain.models import Execution, ExecutionStatus, HealthStatus


def test_domain_module_import_surface():
    modules = [
        "app.shared.domain.entity", "app.shared.domain.aggregate", "app.shared.domain.value_objects",
        "app.shared.domain.rules", "app.shared.domain.state_machine", "app.shared.domain.state_machines",
        "app.shared.domain.events", "app.shared.domain.services", "app.shared.domain.validation",
        "app.modules.organization.domain.models", "app.modules.project.domain.models",
        "app.modules.risk.domain.models", "app.modules.execution.domain.models",
    ]
    for name in modules:
        assert importlib.import_module(name)


def test_state_machine_graphs_have_no_dangling_targets():
    for machine in (ORGANIZATION_STATE_MACHINE, PROJECT_STATE_MACHINE, RISK_STATE_MACHINE, EXECUTION_STATE_MACHINE):
        validate_transition_graph(machine)


def test_organization_terminal_state_and_boundary():
    o = Organization.create("A", "a")
    o.archive()
    with pytest.raises(Exception):
        o.suspend()
    AggregateBoundary.validate(o)


def test_project_terminal_state_and_boundary():
    o = Organization.create("A", "a")
    p = Project.create(o.id, "P")
    p.cancel(); p.archive()
    with pytest.raises(Exception):
        p.activate()
    AggregateBoundary.validate(p)


def test_risk_score_level_boundaries():
    p = uuid4()
    cases = [(1,1,RiskLevel.LOW),(2,2,RiskLevel.LOW),(2,4,RiskLevel.MEDIUM),(4,4,RiskLevel.HIGH),(5,5,RiskLevel.CRITICAL)]
    for probability, impact, level in cases:
        r = Risk.create(p, f"R-{probability}-{impact}")
        r.identify(); r.assess(probability, impact)
        assert r.level is level
        AggregateBoundary.validate(r)


def test_execution_completion_requires_full_progress():
    e = Execution.create(uuid4(), "E")
    e.plan(); e.start()
    with pytest.raises(BusinessRuleViolation):
        e.complete()
    e.update_progress(100)
    e.complete()
    assert e.status is ExecutionStatus.COMPLETED


def test_execution_health_status_boundaries():
    e = Execution.create(uuid4(), "E")
    e.progress = 100; e.budget_spent = 0; e.resources_consumed = 0
    assert e.calculate_health() == 100
    assert e.health_status is HealthStatus.GREEN


def test_aggregate_version_is_monotonic_on_mutation():
    o = Organization.create("A", "a")
    v = o.version
    o.rename("B")
    assert o.version == v + 1
    o.change_slug("b")
    assert o.version == v + 2


def test_stale_version_is_rejected_before_mutation():
    o = Organization.create("A", "a")
    original = (o.name, o.status, o.version)
    with pytest.raises(BusinessRuleViolation):
        o.assert_version(99)
    assert (o.name, o.status, o.version) == original


def test_invalid_aggregate_identity_is_rejected():
    o = Organization.create("A", "a")
    o.id = "bad"
    with pytest.raises(InvalidDomainData):
        o.validate_invariants()


def test_integrated_decision_option_scenario_import_surface():
    assert hasattr(importlib.import_module("app.modules.decision.domain.models"), "Decision")
    assert hasattr(importlib.import_module("app.modules.option.domain.models"), "Option")
    assert hasattr(importlib.import_module("app.modules.scenario.domain.models"), "Scenario")
