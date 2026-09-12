from contextlib import contextmanager
from pathlib import Path
import os, sqlite3
class Database:
    """Transactional DB adapter. SQLite is fully usable locally; PostgreSQL is supported when psycopg is installed."""
    def __init__(self,url=None):
        self.url=url or os.getenv('DATABASE_URL','sqlite:///./decision_intelligence.db')
        self.kind='postgresql' if self.url.startswith(('postgresql://','postgres://')) else 'sqlite'
        if self.kind=='sqlite':
            self.path=Path(self.url.removeprefix('sqlite:///')); self.path.parent.mkdir(parents=True,exist_ok=True)
    @contextmanager
    def transaction(self):
        if self.kind=='sqlite':
            conn=sqlite3.connect(self.path); conn.execute('PRAGMA foreign_keys=ON')
            try: yield conn; conn.commit()
            except Exception: conn.rollback(); raise
            finally: conn.close()
        else:
            try: import psycopg
            except ImportError as e: raise RuntimeError('PostgreSQL requires psycopg[binary] in the deployment environment') from e
            conn=psycopg.connect(self.url)
            try: yield conn; conn.commit()
            except Exception: conn.rollback(); raise
            finally: conn.close()
