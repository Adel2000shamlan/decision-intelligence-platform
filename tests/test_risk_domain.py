import inspect
from uuid import uuid4, UUID
import pytest
from app.modules.risk.domain.models import *
from app.modules.risk.domain.repository import RiskRepository
from app.modules.risk.domain.services import RiskPolicyService
from app.modules.risk.in_memory import InMemoryRiskRepository, DefaultRiskFactory
from app.modules.risk.application.ports import RiskUnitOfWork
from app.modules.risk.application.commands import *
from app.shared.domain.errors import InvalidDomainData, InvalidStateTransition, BusinessRuleViolation, EntityNotFound

def make():
    repo=InMemoryRiskRepository(); uow=RiskUnitOfWork(repo,DefaultRiskFactory(),RiskPolicyService()); return repo,uow,RiskCommandHandler(uow)

def test_entity_and_creation():
    r=Risk.create(uuid4(),'  Revenue decline  ',' desc ',source=RiskSource.AI)
    assert isinstance(r.id,UUID) and r.title=='Revenue decline' and r.version==1 and r.status is RiskStatus.DRAFT
    assert r.source is RiskSource.AI and isinstance(r.pull_events()[0],RiskCreated)

def test_structural_validation():
    for title in ('','   ',None,123):
        with pytest.raises(InvalidDomainData): Risk(uuid4(),title)
    with pytest.raises(InvalidDomainData): Risk('bad','x')
    with pytest.raises(InvalidDomainData): Risk(uuid4(),'x',probability=0)
    with pytest.raises(InvalidDomainData): Risk(uuid4(),'x',impact=6)

def test_lifecycle_and_terminal_archive():
    r=Risk.create(uuid4(),'R'); r.identify(); assert r.status is RiskStatus.IDENTIFIED
    r.assess(4,4); assert (r.score,r.level)==(16,RiskLevel.HIGH)
    r.start_mitigation(); r.monitor(2,2); assert (r.residual_score,r.residual_level)==(4,RiskLevel.LOW)
    r.accept(); r.close(); r.archive(); assert r.status is RiskStatus.ARCHIVED
    v=r.version
    for fn in (r.identify,r.start_mitigation,r.accept,r.close,r.archive):
        with pytest.raises(InvalidStateTransition): fn()
    assert r.version==v

def test_invalid_assessment_does_not_mutate():
    r=Risk.create(uuid4(),'R'); r.identify(); before=(r.status,r.version,r.updated_at)
    with pytest.raises(InvalidDomainData): r.assess(0,3)
    assert (r.status,r.version,r.updated_at)==before

def test_score_and_level_boundaries():
    for p,i,expected in [(1,1,RiskLevel.LOW),(2,2,RiskLevel.LOW),(2,3,RiskLevel.MEDIUM),(3,4,RiskLevel.HIGH),(4,4,RiskLevel.HIGH),(5,5,RiskLevel.CRITICAL)]:
        r=Risk.create(uuid4(),str(p)+str(i)); r.identify(); r.assess(p,i); assert r.level is expected

def test_commands_and_uniqueness():
    repo,uow,h=make(); pid=uuid4(); r=h.create(CreateRisk(pid,'R1')); assert r.version==1
    with pytest.raises(BusinessRuleViolation): h.create(CreateRisk(pid,'R1'))
    h.identify(IdentifyRisk(r.id)); h.assess(AssessRisk(r.id,3,3)); h.start_mitigation(StartRiskMitigation(r.id)); h.monitor(MonitorRisk(r.id,1,2)); h.accept(AcceptRisk(r.id)); h.close(CloseRisk(r.id)); h.archive(ArchiveRisk(r.id))
    assert repo.get_by_id(r.id).status is RiskStatus.ARCHIVED

def test_rename_and_noop_version():
    repo,uow,h=make(); r=h.create(CreateRisk(uuid4(),'Old')); v=r.version; h.rename(RenameRisk(r.id,'Old')); assert r.version==v; h.rename(RenameRisk(r.id,'New')); assert r.version==v+1

def test_residual_guard_is_safe():
    repo,uow,h=make(); r=h.create(CreateRisk(uuid4(),'R')); h.identify(IdentifyRisk(r.id)); h.assess(AssessRisk(r.id,2,2)); h.start_mitigation(StartRiskMitigation(r.id)); before=(r.status,r.version,r.residual_score)
    with pytest.raises(BusinessRuleViolation): h.monitor(MonitorRisk(r.id,5,5))
    assert (r.status,r.version,r.residual_score)==before

def test_not_found():
    _,_,h=make()
    with pytest.raises(EntityNotFound): h.archive(ArchiveRisk(uuid4()))

def test_repository_contract():
    for name in ('get_by_id','list_by_project','list_by_decision','exists_by_title','save'): assert hasattr(RiskRepository,name)

def test_events_and_source():
    r=Risk.create(uuid4(),'R',source=RiskSource.SYSTEM); ev=r.pull_events()[0]; assert ev.source is RiskSource.SYSTEM
    r.identify(); r.assess(1,1); r.start_mitigation(); r.monitor(1,1); r.accept(); r.close(); r.archive(); events=r.pull_events()
    assert [type(x) for x in events]==[RiskIdentified,RiskAssessed,RiskMitigationStarted,RiskMonitored,RiskAccepted,RiskClosed,RiskArchived]

def test_boundary_no_infrastructure_imports():
    import app.modules.risk.domain.models as m, app.modules.risk.domain.repository as repo, app.modules.risk.domain.services as svc
    for mod in (m,repo,svc): assert not any(x in inspect.getsource(mod).lower() for x in ('fastapi','sqlalchemy','postgres','redis','http'))

def test_policy_service():
    repo,uow,h=make(); r=h.create(CreateRisk(uuid4(),'R')); assert r.status is RiskStatus.DRAFT
    with pytest.raises(BusinessRuleViolation): uow.policy.ensure_can_assess(r)

def test_event_metadata():
    actor_id=uuid4(); r=Risk.create(uuid4(),'R',actor_id=actor_id)
    e=r.pull_events()[0]; assert e.event_id and e.occurred_at and e.aggregate_id==r.id and e.actor_id==actor_id
