import sqlite3, json
from datetime import datetime
from uuid import UUID
from app.modules.authentication.security import CredentialRecord, CredentialStatus, PasswordHash, TokenRecord, TokenType, Role
class SQLiteCredentialRepository:
    def __init__(self,db_path=':memory:'):
        self.conn=sqlite3.connect(db_path); self.conn.execute('''CREATE TABLE IF NOT EXISTS credentials(id TEXT PRIMARY KEY,user_id TEXT NOT NULL,algorithm TEXT NOT NULL,iterations INTEGER NOT NULL,salt TEXT NOT NULL,digest TEXT NOT NULL,status TEXT NOT NULL,created_at TEXT NOT NULL,updated_at TEXT NOT NULL,version INTEGER NOT NULL,compromised_at TEXT)'''); self.conn.execute('CREATE UNIQUE INDEX IF NOT EXISTS uq_active_credential ON credentials(user_id) WHERE status="active"'); self.conn.commit()
    def active(self,user_id):
        r=self.conn.execute('SELECT * FROM credentials WHERE user_id=? AND status="active"',(str(user_id),)).fetchone(); return self._row(r) if r else None
    def add(self,c):
        if self.active(c.user_id): raise ValueError('active credential already exists')
        self.conn.execute('INSERT INTO credentials VALUES (?,?,?,?,?,?,?,?,?,?,?)',(str(c.id),str(c.user_id),c.password_hash.algorithm,c.password_hash.iterations,c.password_hash.salt,c.password_hash.digest,c.status.value,c.created_at.isoformat(),c.updated_at.isoformat(),c.version,c.compromised_at.isoformat() if c.compromised_at else None)); self.conn.commit()
    def replace(self,c):
        self.conn.execute('UPDATE credentials SET algorithm=?,iterations=?,salt=?,digest=?,status=?,updated_at=?,version=?,compromised_at=? WHERE id=?',(c.password_hash.algorithm,c.password_hash.iterations,c.password_hash.salt,c.password_hash.digest,c.status.value,c.updated_at.isoformat(),c.version,c.compromised_at.isoformat() if c.compromised_at else None,str(c.id))); self.conn.commit()
    def revoke_user(self,user_id,status=CredentialStatus.REVOKED):
        c=self.active(user_id)
        if not c:return None
        c.status=status;c.version+=1;c.updated_at=datetime.now(c.updated_at.tzinfo);self.replace(c);return c
    def _row(self,r): return CredentialRecord(UUID(r[0]),UUID(r[1]),PasswordHash(r[2],r[3],r[4],r[5]),CredentialStatus(r[6]),datetime.fromisoformat(r[7]),datetime.fromisoformat(r[8]),r[9],datetime.fromisoformat(r[10]) if r[10] else None)
class SQLiteTokenRepository:
    def __init__(self,db_path=':memory:'):
        self.conn=sqlite3.connect(db_path); self.conn.execute('''CREATE TABLE IF NOT EXISTS tokens(token_hash TEXT PRIMARY KEY,token_id TEXT NOT NULL,user_id TEXT NOT NULL,token_type TEXT NOT NULL,issued_at TEXT NOT NULL,expires_at TEXT NOT NULL,session_id TEXT NOT NULL,revoked INTEGER NOT NULL,tenant_id TEXT,roles TEXT NOT NULL)'''); self.conn.commit()
    def put(self,key,r): self.conn.execute('INSERT OR REPLACE INTO tokens VALUES (?,?,?,?,?,?,?,?,?,?)',(key,str(r.token_id),str(r.user_id),r.token_type.value,r.issued_at.isoformat(),r.expires_at.isoformat(),str(r.session_id),int(r.revoked),str(r.tenant_id) if r.tenant_id else None,json.dumps(r.roles))); self.conn.commit()
    def get(self,key):
        r=self.conn.execute('SELECT * FROM tokens WHERE token_hash=?',(key,)).fetchone()
        return TokenRecord(UUID(r[1]),UUID(r[2]),TokenType(r[3]),datetime.fromisoformat(r[4]),datetime.fromisoformat(r[5]),UUID(r[6]),bool(r[7]),UUID(r[8]) if r[8] else None,tuple(json.loads(r[9]))) if r else None
    def revoke(self,key):
        r=self.get(key)
        if r:self.conn.execute('UPDATE tokens SET revoked=1 WHERE token_hash=?',(key,));self.conn.commit()
