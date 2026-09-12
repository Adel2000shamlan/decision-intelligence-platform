import sqlite3
from uuid import UUID
from datetime import datetime
from app.modules.knowledge.domain.models import KnowledgeItem
class KnowledgeRepository:
    def __init__(self,db_path=':memory:'):
        self.conn=sqlite3.connect(db_path); self.conn.execute('''CREATE TABLE IF NOT EXISTS knowledge_items(id TEXT PRIMARY KEY,tenant_id TEXT NOT NULL,title TEXT NOT NULL,content TEXT NOT NULL,source TEXT NOT NULL,project_id TEXT,evidence_uri TEXT,created_at TEXT NOT NULL,version INTEGER NOT NULL)'''); self.conn.execute('CREATE INDEX IF NOT EXISTS idx_knowledge_tenant ON knowledge_items(tenant_id)'); self.conn.commit()
    def save(self,x): self.conn.execute('INSERT OR REPLACE INTO knowledge_items VALUES (?,?,?,?,?,?,?,?,?)',(str(x.id),str(x.tenant_id),x.title,x.content,x.source,str(x.project_id) if x.project_id else None,x.evidence_uri,x.created_at.isoformat(),x.version)); self.conn.commit(); return x
    def get(self,i):
        r=self.conn.execute('SELECT * FROM knowledge_items WHERE id=?',(str(i),)).fetchone(); return self._row(r) if r else None
    def list(self,t): return [self._row(r) for r in self.conn.execute('SELECT * FROM knowledge_items WHERE tenant_id=? ORDER BY created_at',(str(t),))]
    def _row(self,r): return KnowledgeItem(UUID(r[0]),UUID(r[1]),r[2],r[3],r[4],UUID(r[5]) if r[5] else None,r[6],datetime.fromisoformat(r[7]),r[8])
