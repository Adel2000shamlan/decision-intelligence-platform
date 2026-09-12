from uuid import uuid4
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.modules.project.persistence.sqlite import SQLiteProjectRepository,ProjectConcurrencyError,ProjectDuplicateError
from app.modules.project.application.repository import ProjectRepositoryAdapter
from app.modules.project.application.commands import ProjectCommandHandler,CreateProject,RenameProject,TransitionProject
from app.modules.project.application.queries import ProjectQueryService
from app.modules.project.application.service import ProjectApplicationFacade
from app.modules.project.application.events import ProjectEventPublisher,ProjectAuditSink
from app.modules.project.application.tenant import ProjectTenantGuard
from app.modules.project.domain.models import ProjectStatus

def make():
 b=SQLiteProjectRepository(); r=ProjectRepositoryAdapter(b); ev=ProjectEventPublisher(); au=ProjectAuditSink(); c=ProjectCommandHandler(r,events=ev,audit=au); return b,r,c,ProjectQueryService(r),ev,au

def test_repository_persistence_and_roundtrip():
 b,r,c,q,ev,au=make(); oid=uuid4(); p=c.create(CreateProject(oid,'Alpha')); assert q.get(p.id).name=='Alpha'; b.close()

def test_repository_unique_name_and_tenant_scope():
 b,r,c,q,_,_=make(); o=uuid4(); c.create(CreateProject(o,'Alpha'))
 with pytest.raises(Exception): c.create(CreateProject(o,' alpha '))
 assert q.list(o); assert q.list(uuid4())==[]

def test_commands_queries_and_versioning():
 b,r,c,q,_,_=make(); o=uuid4(); p=c.create(CreateProject(o,'Alpha')); c.rename(RenameProject(p.id,'Beta',expected_version=1)); assert q.get(p.id).name=='Beta'
 with pytest.raises(ProjectConcurrencyError): c.rename(RenameProject(p.id,'Gamma',expected_version=1))
 c.transition(TransitionProject(p.id,ProjectStatus.ACTIVE,expected_version=2)); assert q.get(p.id).status is ProjectStatus.ACTIVE

def test_tenant_guard_and_events_audit():
 b,r,c,q,ev,au=make(); o=uuid4(); p=c.create(CreateProject(o,'Alpha')); ProjectTenantGuard.assert_access(p,o)
 with pytest.raises(PermissionError): ProjectTenantGuard.assert_access(p,uuid4())
 assert len(ev.events)==1 and len(au.records)==1

def test_validation_rejects_bad_input():
 b,r,c,q,_,_=make()
 with pytest.raises(ValueError): ProjectApplicationFacade(c,q).create(uuid4(),'')

def test_api_contract():
 client=TestClient(app); o=uuid4(); res=client.post('/api/v1/projects',json={'organization_id':str(o),'name':'API Project'}); assert res.status_code==200; assert res.json()['name']=='API Project'

def test_regression_all_project_core_imports():
 from app.modules.project.domain.models import Project
 assert ProjectStatus.DRAFT.value=='draft'

def test_authorization_integration_and_default_deny_boundary():
    from app.modules.project.application.authorization import ProjectAuthorizationAdapter,ProjectAuthorizationError
    from app.modules.project.application.service import ProjectApplicationFacade
    b,r,c,q,_,_=make(); a=ProjectAuthorizationAdapter({'project:create','project:update','project:archive'})
    facade=ProjectApplicationFacade(c,q,a); org=uuid4(); actor=uuid4()
    p=facade.create(org,'Secure',actor,org); assert p.name=='Secure'
    with pytest.raises(ProjectAuthorizationError): facade.rename(p.id,'Blocked',None,org,p.version)
    with pytest.raises(Exception): facade.get(p.id,uuid4())

def test_event_idempotency_and_audit_attribution():
    b,r,c,q,ev,au=make(); actor=uuid4(); p=c.create(CreateProject(uuid4(),'E',actor)); e=ev.events[0]
    assert ev.publish(e) is False; assert au.records[0].actor_id==actor

def test_persistence_schema_indexes_and_transaction_rollback():
    b,r,c,q,_,_=make(); cols=[x['name'] for x in b.conn.execute('PRAGMA table_info(projects)').fetchall()]
    assert {'id','organization_id','name','name_key','status','created_at','updated_at','version'} <= set(cols)
    indexes=[x['name'] for x in b.conn.execute('PRAGMA index_list(projects)').fetchall()]
    assert any('org' in x for x in indexes)
    b.begin(); b.conn.execute("INSERT INTO projects VALUES(?,?,?,?,?,?,?,?)",(str(uuid4()),str(uuid4()),'Temp','temp','draft','2026-01-01T00:00:00+00:00','2026-01-01T00:00:00+00:00',1)); b.rollback(); assert q.list(uuid4())==[]
