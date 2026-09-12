from .state_machine import StateMachine, validate_transition_graph
from app.modules.organization.domain.models import OrganizationStatus
from app.modules.project.domain.models import ProjectStatus
from app.modules.risk.domain.models import RiskStatus
from app.modules.execution.domain.models import ExecutionStatus
from app.modules.decision.domain.models import DecisionStatus
from app.modules.option.domain.models import OptionStatus
from app.modules.scenario.domain.models import ScenarioStatus
from app.modules.identity.domain.models import UserStatus

USER_STATE_MACHINE = StateMachine({
    UserStatus.ACTIVE: {UserStatus.SUSPENDED, UserStatus.ARCHIVED},
    UserStatus.SUSPENDED: {UserStatus.ACTIVE, UserStatus.ARCHIVED},
    UserStatus.ARCHIVED: set(),
}, terminal={UserStatus.ARCHIVED})

ORGANIZATION_STATE_MACHINE = StateMachine({
    OrganizationStatus.ACTIVE: {OrganizationStatus.SUSPENDED, OrganizationStatus.ARCHIVED},
    OrganizationStatus.SUSPENDED: {OrganizationStatus.ACTIVE, OrganizationStatus.ARCHIVED},
    OrganizationStatus.ARCHIVED: set(),
}, terminal={OrganizationStatus.ARCHIVED})

PROJECT_STATE_MACHINE = StateMachine({
    ProjectStatus.DRAFT: {ProjectStatus.ACTIVE, ProjectStatus.CANCELLED},
    ProjectStatus.ACTIVE: {ProjectStatus.COMPLETED, ProjectStatus.ARCHIVED, ProjectStatus.CANCELLED},
    ProjectStatus.COMPLETED: {ProjectStatus.ARCHIVED},
    ProjectStatus.CANCELLED: {ProjectStatus.ARCHIVED},
    ProjectStatus.ARCHIVED: set(),
}, terminal={ProjectStatus.ARCHIVED})

RISK_STATE_MACHINE = StateMachine({
    RiskStatus.DRAFT: {RiskStatus.IDENTIFIED, RiskStatus.ARCHIVED},
    RiskStatus.IDENTIFIED: {RiskStatus.ASSESSED, RiskStatus.ARCHIVED},
    RiskStatus.ASSESSED: {RiskStatus.MITIGATING, RiskStatus.ACCEPTED, RiskStatus.MONITORED, RiskStatus.ARCHIVED},
    RiskStatus.MITIGATING: {RiskStatus.MONITORED, RiskStatus.ACCEPTED, RiskStatus.CLOSED},
    RiskStatus.MONITORED: {RiskStatus.MITIGATING, RiskStatus.ACCEPTED, RiskStatus.CLOSED, RiskStatus.ARCHIVED},
    RiskStatus.ACCEPTED: {RiskStatus.CLOSED, RiskStatus.ARCHIVED},
    RiskStatus.CLOSED: {RiskStatus.ARCHIVED},
    RiskStatus.ARCHIVED: set(),
}, terminal={RiskStatus.ARCHIVED})

EXECUTION_STATE_MACHINE = StateMachine({
    ExecutionStatus.DRAFT: {ExecutionStatus.PLANNED, ExecutionStatus.CANCELLED, ExecutionStatus.ARCHIVED},
    ExecutionStatus.PLANNED: {ExecutionStatus.IN_PROGRESS, ExecutionStatus.CANCELLED, ExecutionStatus.ARCHIVED},
    ExecutionStatus.IN_PROGRESS: {ExecutionStatus.AT_RISK, ExecutionStatus.BLOCKED, ExecutionStatus.COMPLETED, ExecutionStatus.CANCELLED},
    ExecutionStatus.AT_RISK: {ExecutionStatus.IN_PROGRESS, ExecutionStatus.BLOCKED, ExecutionStatus.COMPLETED, ExecutionStatus.CANCELLED},
    ExecutionStatus.BLOCKED: {ExecutionStatus.IN_PROGRESS, ExecutionStatus.AT_RISK, ExecutionStatus.CANCELLED},
    ExecutionStatus.COMPLETED: {ExecutionStatus.ARCHIVED},
    ExecutionStatus.CANCELLED: {ExecutionStatus.ARCHIVED},
    ExecutionStatus.ARCHIVED: set(),
}, terminal={ExecutionStatus.ARCHIVED})

DECISION_STATE_MACHINE = StateMachine({
    DecisionStatus.DRAFT: {DecisionStatus.ANALYSIS, DecisionStatus.CANCELLED},
    DecisionStatus.ANALYSIS: {DecisionStatus.READY_FOR_APPROVAL, DecisionStatus.CANCELLED},
    DecisionStatus.READY_FOR_APPROVAL: {DecisionStatus.APPROVED, DecisionStatus.REJECTED, DecisionStatus.CANCELLED},
    DecisionStatus.APPROVED: {DecisionStatus.EXECUTED, DecisionStatus.CANCELLED},
    DecisionStatus.REJECTED: {DecisionStatus.ANALYSIS, DecisionStatus.CANCELLED},
    DecisionStatus.EXECUTED: {DecisionStatus.CLOSED},
    DecisionStatus.CANCELLED: set(),
    DecisionStatus.CLOSED: set(),
}, terminal={DecisionStatus.CANCELLED, DecisionStatus.CLOSED})

OPTION_STATE_MACHINE = StateMachine({
    OptionStatus.DRAFT: {OptionStatus.UNDER_EVALUATION, OptionStatus.WITHDRAWN, OptionStatus.ARCHIVED},
    OptionStatus.UNDER_EVALUATION: {OptionStatus.ELIGIBLE, OptionStatus.REJECTED, OptionStatus.WITHDRAWN},
    OptionStatus.ELIGIBLE: {OptionStatus.SELECTED, OptionStatus.REJECTED, OptionStatus.WITHDRAWN},
    OptionStatus.SELECTED: {OptionStatus.ARCHIVED},
    OptionStatus.REJECTED: {OptionStatus.DRAFT, OptionStatus.WITHDRAWN, OptionStatus.ARCHIVED},
    OptionStatus.WITHDRAWN: {OptionStatus.ARCHIVED},
    OptionStatus.ARCHIVED: set(),
}, terminal={OptionStatus.ARCHIVED})

SCENARIO_STATE_MACHINE = StateMachine({
    ScenarioStatus.DRAFT: {ScenarioStatus.UNDER_ANALYSIS, ScenarioStatus.ARCHIVED},
    ScenarioStatus.UNDER_ANALYSIS: {ScenarioStatus.EVALUATED, ScenarioStatus.REJECTED, ScenarioStatus.ARCHIVED},
    ScenarioStatus.EVALUATED: {ScenarioStatus.APPROVED, ScenarioStatus.REJECTED, ScenarioStatus.UNDER_ANALYSIS, ScenarioStatus.ARCHIVED},
    ScenarioStatus.APPROVED: {ScenarioStatus.ARCHIVED},
    ScenarioStatus.REJECTED: {ScenarioStatus.DRAFT, ScenarioStatus.ARCHIVED},
    ScenarioStatus.ARCHIVED: set(),
}, terminal={ScenarioStatus.ARCHIVED})

for _machine in (USER_STATE_MACHINE, ORGANIZATION_STATE_MACHINE, PROJECT_STATE_MACHINE, RISK_STATE_MACHINE, EXECUTION_STATE_MACHINE, DECISION_STATE_MACHINE, OPTION_STATE_MACHINE, SCENARIO_STATE_MACHINE):
    validate_transition_graph(_machine)
