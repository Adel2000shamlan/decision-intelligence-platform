from app.shared.domain.state_machine import StateMachine, validate_transition_graph
from app.shared.domain.errors import InvalidStateTransition
from app.shared.domain.state_machines import ORGANIZATION_STATE_MACHINE, PROJECT_STATE_MACHINE, RISK_STATE_MACHINE, EXECUTION_STATE_MACHINE
from app.modules.organization.domain.models import OrganizationStatus
from app.modules.project.domain.models import ProjectStatus
from app.modules.risk.domain.models import RiskStatus
from app.modules.execution.domain.models import ExecutionStatus
import pytest

def test_graphs_have_no_dangling_targets():
    for m in (ORGANIZATION_STATE_MACHINE, PROJECT_STATE_MACHINE, RISK_STATE_MACHINE, EXECUTION_STATE_MACHINE): validate_transition_graph(m)

def test_organization_terminal():
    assert ORGANIZATION_STATE_MACHINE.is_terminal(OrganizationStatus.ARCHIVED)
    with pytest.raises(InvalidStateTransition): ORGANIZATION_STATE_MACHINE.transition(OrganizationStatus.ARCHIVED, OrganizationStatus.ACTIVE)

def test_project_cancel_then_archive():
    assert PROJECT_STATE_MACHINE.can_transition(ProjectStatus.ACTIVE, ProjectStatus.CANCELLED)
    assert PROJECT_STATE_MACHINE.transition(ProjectStatus.CANCELLED, ProjectStatus.ARCHIVED) is ProjectStatus.ARCHIVED

def test_risk_workflow():
    assert RISK_STATE_MACHINE.can_transition(RiskStatus.IDENTIFIED, RiskStatus.ASSESSED)
    assert not RISK_STATE_MACHINE.can_transition(RiskStatus.DRAFT, RiskStatus.MONITORED)

def test_execution_workflow():
    assert EXECUTION_STATE_MACHINE.can_transition(ExecutionStatus.BLOCKED, ExecutionStatus.IN_PROGRESS)
    assert not EXECUTION_STATE_MACHINE.can_transition(ExecutionStatus.COMPLETED, ExecutionStatus.IN_PROGRESS)

def test_machine_is_non_mutating_and_reusable():
    m=StateMachine({'a': {'b'}, 'b': set()}, terminal={'b'})
    assert m.transition('a','b') == 'b'
    assert m.allowed_targets('a') == frozenset({'b'})
    assert m.is_terminal('b')
