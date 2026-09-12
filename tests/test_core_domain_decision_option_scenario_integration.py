from uuid import uuid4
import pytest
from app.shared.domain.aggregate import AggregateBoundary
from app.shared.domain.errors import BusinessRuleViolation, EntityNotFound
from app.shared.domain.state_machines import DECISION_STATE_MACHINE, OPTION_STATE_MACHINE, SCENARIO_STATE_MACHINE
from app.shared.domain.state_machine import validate_transition_graph
from app.shared.domain.validation import DomainValidator
from app.modules.decision.domain.models import Decision, DecisionStatus
from app.modules.decision.domain.services import DecisionDomainService
from app.modules.decision.in_memory import InMemoryDecisionRepository
from app.modules.option.domain.models import Option, OptionStatus, OptionSource, OptionType
from app.modules.option.domain.services import OptionDomainService
from app.modules.option.in_memory import InMemoryOptionRepository
from app.modules.scenario.domain.models import Scenario, ScenarioStatus
from app.modules.scenario.domain.services import ScenarioDomainService
from app.modules.scenario.in_memory import InMemoryScenarioRepository


def test_all_three_are_aggregate_roots_and_validate():
    org, project = uuid4(), uuid4()
    d = Decision.create(org, project, 'D')
    o = Option.create(d.id, 'Original')
    s = Scenario.create(d.id, o.id, 'Base')
    for root in (d, o, s):
        AggregateBoundary.validate(root)
        DomainValidator.validate_aggregate(root)
        assert root.aggregate_id == root.id
        assert root.aggregate_version >= 1


def test_decision_option_scenario_lifecycle_and_human_gates():
    dr, orp, sr = InMemoryDecisionRepository(), InMemoryOptionRepository(), InMemoryScenarioRepository()
    decision = DecisionDomainService().create(dr, uuid4(), uuid4(), 'D').entity
    option = OptionDomainService().create(orp, dr, decision.id, 'Original').entity
    scenario = ScenarioDomainService().create(sr, dr, orp, decision.id, option.id, 'Base').entity
    ds, os, ss = DecisionDomainService(), OptionDomainService(), ScenarioDomainService()
    ds.start_analysis(dr, decision.id)
    ds.submit_for_approval(dr, decision.id)
    with pytest.raises(BusinessRuleViolation): ds.approve(dr, decision.id)
    ds.approve(dr, decision.id, actor_id=uuid4())
    assert dr.get_by_id(decision.id).status is DecisionStatus.APPROVED
    os.start_evaluation(orp, option.id); os.mark_eligible(orp, option.id); os.select(orp, option.id)
    ss.start_analysis(sr, scenario.id); ss.evaluate(sr, scenario.id)
    with pytest.raises(BusinessRuleViolation): ss.approve(sr, scenario.id)
    ss.approve(sr, scenario.id, actor_id=uuid4())
    assert orp.get_by_id(option.id).status is OptionStatus.SELECTED
    assert sr.get_by_id(scenario.id).status is ScenarioStatus.APPROVED


def test_cross_aggregate_creation_boundaries():
    dr, orp, sr = InMemoryDecisionRepository(), InMemoryOptionRepository(), InMemoryScenarioRepository()
    svc = OptionDomainService()
    with pytest.raises(Exception): svc.create(orp, dr, uuid4(), 'O')
    decision = DecisionDomainService().create(dr, uuid4(), uuid4(), 'D').entity
    with pytest.raises(BusinessRuleViolation): svc.create(orp, dr, decision.id, 'AI bad', option_type=OptionType.ORIGINAL, source=OptionSource.AI)
    option = svc.create(orp, dr, decision.id, 'AI good', option_type=OptionType.ALTERNATIVE, source=OptionSource.AI).entity
    ssvc=ScenarioDomainService()
    with pytest.raises(EntityNotFound): ssvc.create(sr, dr, orp, decision.id, uuid4(), 'bad')
    scenario=ssvc.create(sr, dr, orp, decision.id, option.id, 'Base').entity
    assert scenario.option_id == option.id


def test_central_state_machine_graphs_for_integrated_roots():
    for machine in (DECISION_STATE_MACHINE, OPTION_STATE_MACHINE, SCENARIO_STATE_MACHINE):
        validate_transition_graph(machine)
    assert DECISION_STATE_MACHINE.can_transition(DecisionStatus.DRAFT, DecisionStatus.ANALYSIS)
    assert not DECISION_STATE_MACHINE.can_transition(DecisionStatus.CLOSED, DecisionStatus.ANALYSIS)
    assert OPTION_STATE_MACHINE.can_transition(OptionStatus.ELIGIBLE, OptionStatus.SELECTED)
    assert SCENARIO_STATE_MACHINE.can_transition(ScenarioStatus.EVALUATED, ScenarioStatus.APPROVED)


def test_ai_option_governance_cannot_be_bypassed_by_update():
    option = Option.create(uuid4(), 'A', option_type=OptionType.ALTERNATIVE, source=OptionSource.AI)
    with pytest.raises(BusinessRuleViolation):
        option.update(source=OptionSource.AI, option_type=OptionType.ORIGINAL)
