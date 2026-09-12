import sqlite3
from uuid import UUID
from datetime import datetime
from app.modules.agent.domain.models import Agent
class AgentRepository:
    def __init__(self,db_path=':memory:'):
        self.conn=sqlite3.connect(db_path); self.conn.execute('''CREATE TABLE IF NOT EXISTS agents(id TEXT PRIMARY KEY,tenant_id TEXT NOT NULL,name TEXT NOT NULL,capabilities TEXT NOT NULL,enabled INTEGER NOT NULL,created_at TEXT NOT NULL,UNIQUE(tenant_id,name))'''); self.conn.commit()
    def save(self,a): self.conn.execute('INSERT OR REPLACE INTO agents VALUES (?,?,?,?,?,?)',(str(a.id),str(a.tenant_id),a.name,','.join(sorted(a.capabilities)),int(a.enabled),a.created_at.isoformat())); self.conn.commit(); return a
    def get(self,i):
        r=self.conn.execute('SELECT * FROM agents WHERE id=?',(str(i),)).fetchone(); return self._row(r) if r else None
    def list(self,t): return [self._row(r) for r in self.conn.execute('SELECT * FROM agents WHERE tenant_id=?',(str(t),))]
    def _row(self,r): return Agent(UUID(r[0]),UUID(r[1]),r[2],frozenset(filter(None,r[3].split(','))),bool(r[4]),datetime.fromisoformat(r[5]))
