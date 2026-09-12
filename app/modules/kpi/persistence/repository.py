import sqlite3
from uuid import UUID
from datetime import datetime
from app.modules.kpi.domain.models import KPI
class KPIRepository:
    def __init__(self, db_path=':memory:'):
        self.conn=sqlite3.connect(db_path); self.conn.execute('PRAGMA foreign_keys=ON'); self.conn.execute('''CREATE TABLE IF NOT EXISTS kpis(id TEXT PRIMARY KEY,tenant_id TEXT NOT NULL,name TEXT NOT NULL,unit TEXT NOT NULL,target REAL NOT NULL,actual REAL NOT NULL,project_id TEXT,created_at TEXT NOT NULL,updated_at TEXT NOT NULL,version INTEGER NOT NULL,UNIQUE(tenant_id,name))'''); self.conn.execute('CREATE INDEX IF NOT EXISTS idx_kpis_tenant ON kpis(tenant_id)'); self.conn.commit()
    def save(self,k):
        row=self.conn.execute('SELECT version FROM kpis WHERE id=?',(str(k.id),)).fetchone()
        if row and row[0] != k.version-1: raise RuntimeError('optimistic concurrency conflict')
        if row: self.conn.execute('UPDATE kpis SET name=?,unit=?,target=?,actual=?,project_id=?,updated_at=?,version=? WHERE id=?',(k.name,k.unit,k.target,k.actual,str(k.project_id) if k.project_id else None,k.updated_at.isoformat(),k.version,str(k.id)))
        else: self.conn.execute('INSERT INTO kpis VALUES (?,?,?,?,?,?,?,?,?,?)',(str(k.id),str(k.tenant_id),k.name,k.unit,k.target,k.actual,str(k.project_id) if k.project_id else None,k.created_at.isoformat(),k.updated_at.isoformat(),k.version))
        self.conn.commit(); return k
    def get(self,kid):
        r=self.conn.execute('SELECT * FROM kpis WHERE id=?',(str(kid),)).fetchone(); return self._row(r) if r else None
    def list(self,tenant_id): return [self._row(r) for r in self.conn.execute('SELECT * FROM kpis WHERE tenant_id=? ORDER BY created_at',(str(tenant_id),))]
    def _row(self,r): return KPI(UUID(r[0]),UUID(r[1]),r[2],r[3],r[4],r[5],UUID(r[6]) if r[6] else None,datetime.fromisoformat(r[7]),datetime.fromisoformat(r[8]),r[9])
