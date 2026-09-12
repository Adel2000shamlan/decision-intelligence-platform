import sqlite3
from datetime import datetime, timezone
from uuid import UUID
from app.modules.organization.domain.models import Organization, OrganizationStatus

class SQLiteOrganizationRepository:
    def __init__(self, path=':memory:'):
        self.conn=sqlite3.connect(path, check_same_thread=False); self.conn.row_factory=sqlite3.Row; self._init()
    def _init(self):
        self.conn.execute("CREATE TABLE IF NOT EXISTS organizations (id TEXT PRIMARY KEY, tenant_id TEXT, name TEXT NOT NULL, slug TEXT NOT NULL UNIQUE, status TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL, version INTEGER NOT NULL)"); self.conn.execute('CREATE INDEX IF NOT EXISTS idx_org_tenant ON organizations(tenant_id)'); self.conn.commit()
    def save(self, organization, tenant_id=None):
        now=lambda x: x.isoformat()
        self.conn.execute("INSERT INTO organizations(id,tenant_id,name,slug,status,created_at,updated_at,version) VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET tenant_id=excluded.tenant_id,name=excluded.name,slug=excluded.slug,status=excluded.status,updated_at=excluded.updated_at,version=excluded.version",(str(organization.id),str(tenant_id) if tenant_id else None,organization.name,organization.slug,organization.status.value,now(organization.created_at),now(organization.updated_at),organization.version)); self.conn.commit(); return organization
    def _row(self,row):
        if not row:return None
        return Organization(id=UUID(row['id']),name=row['name'],slug=row['slug'],status=OrganizationStatus(row['status']),created_at=datetime.fromisoformat(row['created_at']),updated_at=datetime.fromisoformat(row['updated_at']),version=row['version'])
    def get_by_id(self, organization_id): return self._row(self.conn.execute('SELECT * FROM organizations WHERE id=?',(str(organization_id),)).fetchone())
    def get_by_slug(self, slug): return self._row(self.conn.execute('SELECT * FROM organizations WHERE slug=?',(slug.strip().lower(),)).fetchone())
    def exists_by_slug(self, slug): return self.get_by_slug(slug) is not None
    def list(self, tenant_id=None):
        q='SELECT * FROM organizations'; args=()
        if tenant_id is not None:q+=' WHERE tenant_id=?'; args=(str(tenant_id),)
        return [self._row(r) for r in self.conn.execute(q,args).fetchall()]
