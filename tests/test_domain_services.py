from uuid import uuid4
import pytest
from app.shared.domain.errors import BusinessRuleViolation, EntityNotFound
from app.modules.organization.in_memory import InMemoryOrganizationRepository
from app.modules.organization.domain.services import OrganizationDomainService
from app.modules.project.in_memory import InMemoryProjectRepository
from app.modules.project.domain.services import ProjectDomainService
from app.modules.risk.in_memory import InMemoryRiskRepository
from app.modules.risk.domain.services import RiskDomainService
from app.modules.execution.in_memory import InMemoryExecutionRepository
from app.modules.execution.domain.services import ExecutionDomainService


def test_organization_service_create_and_lifecycle():
    repo=InMemoryOrganizationRepository(); s=OrganizationDomainService()
    r=s.create(repo,'Acme','acme'); assert r.entity.name=='Acme'; assert len(r.events)==1
    oid=r.entity.id; r=s.suspend(repo,oid,expected_version=1); assert r.entity.status.value=='suspended'; assert len(r.events)==1
    s.reactivate(repo,oid); s.archive(repo,oid)
    with pytest.raises(BusinessRuleViolation): s.rename(repo,oid,'Nope')

def test_organization_service_uniqueness_and_version():
    repo=InMemoryOrganizationRepository(); s=OrganizationDomainService(); a=s.create(repo,'A','same').entity
    with pytest.raises(BusinessRuleViolation): s.create(repo,'B','same')
    with pytest.raises(BusinessRuleViolation): s.suspend(repo,a.id,expected_version=99)

def test_project_service_requires_active_org_and_unique_name():
    orp=InMemoryOrganizationRepository(); pr=InMemoryProjectRepository(); os=OrganizationDomainService(); ps=ProjectDomainService()
    org=os.create(orp,'Acme','acme').entity
    p=ps.create(pr,orp,org.id,'P').entity; assert p.status.value=='draft'
    with pytest.raises(BusinessRuleViolation): ps.create(pr,orp,org.id,'P')
    os.suspend(orp,org.id)
    with pytest.raises(BusinessRuleViolation): ps.create(pr,orp,org.id,'Q')

def test_project_service_transitions_and_events():
    orp=InMemoryOrganizationRepository(); pr=InMemoryProjectRepository(); org=OrganizationDomainService().create(orp,'A','a').entity; s=ProjectDomainService(); p=s.create(pr,orp,org.id,'P').entity
    r=s.activate(pr,p.id); assert r.entity.status.value=='active' and r.events
    r=s.complete(pr,p.id); assert r.entity.status.value=='completed'
    s.archive(pr,p.id)
    with pytest.raises(BusinessRuleViolation): s.rename(pr,p.id,'X')

def test_risk_service_assess_monitor_guard_and_events():
    repo=InMemoryRiskRepository(); s=RiskDomainService(); p=uuid4(); r=s.create(repo,p,'R').entity
    s.identify(repo,r.id); a=s.assess(repo,r.id,2,3); assert a.entity.score==6 and a.events
    with pytest.raises(BusinessRuleViolation): s.monitor(repo,r.id,5,5)
    assert a.entity.residual_score is None
    m=s.monitor(repo,r.id,1,2); assert m.entity.residual_score==2
    s.accept(repo,r.id); s.close(repo,r.id); s.archive(repo,r.id)

def test_risk_service_uniqueness_not_found_and_version():
    repo=InMemoryRiskRepository(); s=RiskDomainService(); p=uuid4(); r=s.create(repo,p,'R').entity
    with pytest.raises(BusinessRuleViolation): s.create(repo,p,'R')
    with pytest.raises(EntityNotFound): s.identify(repo,uuid4())
    with pytest.raises(BusinessRuleViolation): s.identify(repo,r.id,expected_version=42)

def test_execution_service_lifecycle_and_metrics():
    repo=InMemoryExecutionRepository(); s=ExecutionDomainService(); p=uuid4(); e=s.create(repo,p,'E').entity
    s.plan(repo,e.id); s.start(repo,e.id); s.update_progress(repo,e.id,100); s.complete(repo,e.id)
    r=s.calculate_health(repo,e.id); assert r.entity.health_score is not None
    s.archive(repo,e.id)
    with pytest.raises(BusinessRuleViolation): s.rename(repo,e.id,'X')

def test_execution_service_uniqueness_and_version():
    repo=InMemoryExecutionRepository(); s=ExecutionDomainService(); p=uuid4(); e=s.create(repo,p,'E').entity
    with pytest.raises(BusinessRuleViolation): s.create(repo,p,'E')
    with pytest.raises(BusinessRuleViolation): s.plan(repo,e.id,expected_version=999)

def test_service_result_consumes_pending_events_only():
    repo=InMemoryOrganizationRepository(); s=OrganizationDomainService(); r=s.create(repo,'A','a').entity
    assert r.pull_events()==()
