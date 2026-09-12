import sqlite3
class SQLiteRBAC:
    def __init__(self,db_path=':memory:'):
        self.conn=sqlite3.connect(db_path); self.conn.execute('CREATE TABLE IF NOT EXISTS roles(name TEXT PRIMARY KEY,permissions TEXT NOT NULL)'); self.conn.execute('CREATE TABLE IF NOT EXISTS role_assignments(user_id TEXT NOT NULL,tenant_id TEXT NOT NULL,role TEXT NOT NULL,PRIMARY KEY(user_id,tenant_id,role),FOREIGN KEY(role) REFERENCES roles(name))'); self.conn.commit()
    def define(self,role,permissions):
        import json; self.conn.execute('INSERT OR REPLACE INTO roles VALUES (?,?)',(role,json.dumps(sorted(set(permissions))))); self.conn.commit()
    def assign(self,user_id,role,tenant_id):
        if not self.conn.execute('SELECT 1 FROM roles WHERE name=?',(role,)).fetchone(): raise ValueError('unknown role')
        self.conn.execute('INSERT OR IGNORE INTO role_assignments VALUES (?,?,?)',(str(user_id),str(tenant_id),role)); self.conn.commit()
    def permissions(self,user_id,tenant_id):
        import json
        out=set()
        for (p,) in self.conn.execute('SELECT r.permissions FROM role_assignments a JOIN roles r ON r.name=a.role WHERE a.user_id=? AND a.tenant_id=?',(str(user_id),str(tenant_id))): out.update(json.loads(p))
        return frozenset(out)
    def require(self,user_id,tenant_id,permission):
        if permission not in self.permissions(user_id,tenant_id): raise PermissionError('permission denied')
