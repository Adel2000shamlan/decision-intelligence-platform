from datetime import datetime, timezone
MIGRATION_ID='105.02.001'
TABLES={
 'organizations': 'CREATE TABLE IF NOT EXISTS organizations(id TEXT PRIMARY KEY,tenant_id TEXT NOT NULL,name TEXT NOT NULL,slug TEXT NOT NULL,status TEXT NOT NULL,created_at TEXT NOT NULL,updated_at TEXT NOT NULL,version INTEGER NOT NULL,UNIQUE(tenant_id,slug))',
 'projects': 'CREATE TABLE IF NOT EXISTS projects(id TEXT PRIMARY KEY,organization_id TEXT NOT NULL,name TEXT NOT NULL,name_key TEXT NOT NULL,status TEXT NOT NULL,created_at TEXT NOT NULL,updated_at TEXT NOT NULL,version INTEGER NOT NULL,UNIQUE(organization_id,name_key))',
 'decisions': 'CREATE TABLE IF NOT EXISTS decisions(id TEXT PRIMARY KEY,organization_id TEXT NOT NULL,project_id TEXT NOT NULL,title TEXT NOT NULL,title_key TEXT NOT NULL,status TEXT NOT NULL,created_at TEXT NOT NULL,updated_at TEXT NOT NULL,version INTEGER NOT NULL,UNIQUE(project_id,title_key))',
 'options': 'CREATE TABLE IF NOT EXISTS options(id TEXT PRIMARY KEY,decision_id TEXT NOT NULL,title TEXT NOT NULL,title_key TEXT NOT NULL,status TEXT NOT NULL,created_at TEXT NOT NULL,updated_at TEXT NOT NULL,version INTEGER NOT NULL,UNIQUE(decision_id,title_key))',
 'scenarios': 'CREATE TABLE IF NOT EXISTS scenarios(id TEXT PRIMARY KEY,decision_id TEXT NOT NULL,option_id TEXT NOT NULL,name TEXT NOT NULL,name_key TEXT NOT NULL,status TEXT NOT NULL,created_at TEXT NOT NULL,updated_at TEXT NOT NULL,version INTEGER NOT NULL,UNIQUE(decision_id,name_key))',
 'risks': 'CREATE TABLE IF NOT EXISTS risks(id TEXT PRIMARY KEY,project_id TEXT NOT NULL,decision_id TEXT,title TEXT NOT NULL,title_key TEXT NOT NULL,status TEXT NOT NULL,created_at TEXT NOT NULL,updated_at TEXT NOT NULL,version INTEGER NOT NULL,UNIQUE(project_id,title_key))',
 'executions': 'CREATE TABLE IF NOT EXISTS executions(id TEXT PRIMARY KEY,project_id TEXT NOT NULL,title TEXT NOT NULL,title_key TEXT NOT NULL,status TEXT NOT NULL,progress REAL NOT NULL,created_at TEXT NOT NULL,updated_at TEXT NOT NULL,version INTEGER NOT NULL,UNIQUE(project_id,title_key))',
 'kpis': 'CREATE TABLE IF NOT EXISTS kpis(id TEXT PRIMARY KEY,tenant_id TEXT NOT NULL,name TEXT NOT NULL,unit TEXT NOT NULL,target REAL NOT NULL,actual REAL NOT NULL,project_id TEXT,created_at TEXT NOT NULL,updated_at TEXT NOT NULL,version INTEGER NOT NULL,UNIQUE(tenant_id,name))',
 'knowledge_items': 'CREATE TABLE IF NOT EXISTS knowledge_items(id TEXT PRIMARY KEY,tenant_id TEXT NOT NULL,title TEXT NOT NULL,content TEXT NOT NULL,source TEXT NOT NULL,project_id TEXT,evidence_uri TEXT,created_at TEXT NOT NULL,version INTEGER NOT NULL)',
 'agents': 'CREATE TABLE IF NOT EXISTS agents(id TEXT PRIMARY KEY,tenant_id TEXT NOT NULL,name TEXT NOT NULL,capabilities TEXT NOT NULL,enabled INTEGER NOT NULL,created_at TEXT NOT NULL,UNIQUE(tenant_id,name))',
}
def _placeholder(conn):
    return '%s' if type(conn).__module__.startswith('psycopg') else '?'

def _execute(conn, sql, params=()):
    if params:
        sql = sql.replace('?', _placeholder(conn))
        return conn.execute(sql, params)
    return conn.execute(sql)


def apply_initial(conn):
    _execute(conn, 'CREATE TABLE IF NOT EXISTS schema_migrations(version TEXT PRIMARY KEY,applied_at TEXT NOT NULL)')
    for sql in TABLES.values(): _execute(conn, sql)
    for table in ('organizations','projects','decisions','options','scenarios','risks','executions','kpis','knowledge_items','agents'):
        _execute(conn, f'CREATE INDEX IF NOT EXISTS idx_{table}_tenant ON {table}(tenant_id)' if table not in ('projects','decisions','options','scenarios','risks','executions') else 'SELECT 1')
    if _execute(conn, 'SELECT 1 FROM schema_migrations WHERE version=?',(MIGRATION_ID,)).fetchone() is None:
        _execute(conn, 'INSERT INTO schema_migrations(version,applied_at) VALUES (?,?)',(MIGRATION_ID,datetime.now(timezone.utc).isoformat()))
def rollback_initial(conn):
    # Rollback is explicit and destructive; callers must execute inside a transaction.
    for t in reversed(tuple(TABLES)): _execute(conn, f'DROP TABLE IF EXISTS {t}')
    _execute(conn, 'DELETE FROM schema_migrations WHERE version=?',(MIGRATION_ID,))
