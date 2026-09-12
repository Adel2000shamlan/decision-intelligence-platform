from pathlib import Path
from app.infrastructure.database import Database
from app.infrastructure.migrations import apply_initial, rollback_initial
from app.infrastructure.events import EventStore, StoredEvent
from app.infrastructure.audit import TamperEvidentAudit
from app.infrastructure.cache import TTLCache
from app.infrastructure.jobs import JobQueue, Job
from app.infrastructure.gateway import APIGateway, GatewayRequest
from app.infrastructure.security import SecretBoundary
from app.infrastructure.backup import BackupManager

def test_database_and_migration(tmp_path):
    db=Database(f"sqlite:///{tmp_path/'x.db'}")
    with db.transaction() as c:
        apply_initial(c)
        assert c.execute("select count(*) from schema_migrations").fetchone()[0]==1
        rollback_initial(c)
        assert c.execute("select count(*) from schema_migrations").fetchone()[0]==0

def test_event_idempotency():
    s=EventStore(); e=StoredEvent('1','x','a',{})
    assert s.append(e) is True and s.append(e) is False

def test_audit_chain():
    a=TamperEvidentAudit(); a.append('create','u','x'); a.append('update','u','x'); assert a.verify()

def test_cache_and_jobs():
    c=TTLCache(); c.set('a',1); assert c.get('a')==1
    q=JobQueue(); j=Job('1','x'); q.enqueue(j); assert q.run_once(lambda x:None).status=='COMPLETED'

def test_gateway_security():
    g=APIGateway(); assert g.validate(GatewayRequest('GET','/api/v1/x','u','t',{}))
    SecretBoundary.assert_safe({'name':'ok'})

def test_backup(tmp_path):
    src=tmp_path/'a'; src.write_text('ok'); dst=tmp_path/'b'; BackupManager().backup(src,dst); assert dst.read_text()=='ok'
