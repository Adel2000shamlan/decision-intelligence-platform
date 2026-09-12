from uuid import uuid4
from app.infrastructure.database import Database
from app.infrastructure.migrations import apply_initial, rollback_initial, TABLES
from app.infrastructure.backup import BackupManager
from app.infrastructure.audit import TamperEvidentAudit
from app.infrastructure.security import SecretBoundary
from app.infrastructure.gateway import APIGateway, GatewayRequest
from app.modules.kpi.application.service import KPIApplicationService
from app.modules.knowledge.application.service import KnowledgeApplicationService
from app.modules.agent.application.service import AgentApplicationService
from app.modules.authentication.security import CredentialService

def test_real_schema_migration_creates_domain_tables(tmp_path):
    db=Database(f'sqlite:///{tmp_path}/x.db')
    with db.transaction() as c:
        apply_initial(c)
        assert all(c.execute("select name from sqlite_master where type='table' and name=?",(n,)).fetchone() for n in TABLES)
    with db.transaction() as c: rollback_initial(c)

def test_kpi_knowledge_agent_are_concrete_and_tenant_scoped(tmp_path):
    t=uuid4(); k=KPIApplicationService(); x=k.create(t,'Revenue','EGP',100,90); assert k.get(x.id).achievement_ratio==.9; assert len(k.list(t))==1
    n=KnowledgeApplicationService(); item=n.create(t,'Policy','content','internal'); assert n.get(item.id).tenant_id==t
    a=AgentApplicationService(); agent=a.register(t,'Planner',['analyze']); assert agent.enabled and 'analyze' in agent.capabilities

def test_password_history_contains_no_plaintext():
    c=CredentialService(); uid=uuid4(); c.register(uid,'StrongPass123!'); assert all(not isinstance(x,str) for x in c.history[uid])
    try: c.register(uuid4(),'AnotherStrong123!')
    except Exception: pass

def test_backup_checksum_and_audit_tamper_detection(tmp_path):
    src=tmp_path/'a'; dst=tmp_path/'b'; src.write_text('ok'); b=BackupManager(); b.backup(src,dst); assert b.sha256(src)==b.sha256(dst)
    a=TamperEvidentAudit(); r=a.append('x','u','s'); assert a.verify(); a.records[0]=type(r)(r.sequence,r.action,r.actor_id,r.subject_id,r.occurred_at,{'tampered':1},r.previous_hash,r.record_hash); assert not a.verify()

def test_security_boundary_and_gateway_fail_closed():
    try: SecretBoundary.assert_safe({'access_token':'x'})
    except ValueError: pass
    else: assert False
    g=APIGateway(); assert g.validate(GatewayRequest('GET','/api/v1/x','u','t',{}))
    try: g.validate(GatewayRequest('TRACE','/api/v1/x','u','t',{}))
    except ValueError: pass
    else: assert False
