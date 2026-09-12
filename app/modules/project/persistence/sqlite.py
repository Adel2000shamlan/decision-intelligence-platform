from __future__ import annotations
import sqlite3
from datetime import datetime
from uuid import UUID
from app.modules.project.domain.models import Project, ProjectStatus

class ProjectRepositoryError(Exception): pass
class ProjectNotFound(ProjectRepositoryError): pass
class ProjectConcurrencyError(ProjectRepositoryError): pass
class ProjectDuplicateError(ProjectRepositoryError): pass

class SQLiteProjectRepository:
    """Durable Project repository with tenant-scoped queries and optimistic concurrency."""
    def __init__(self, path=':memory:', connection=None):
        self.conn = connection or sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()
    def _init_schema(self):
        self.conn.executescript('''
        CREATE TABLE IF NOT EXISTS projects (
          id TEXT PRIMARY KEY,
          organization_id TEXT NOT NULL,
          name TEXT NOT NULL,
          name_key TEXT NOT NULL,
          status TEXT NOT NULL,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL,
          version INTEGER NOT NULL CHECK(version >= 1),
          UNIQUE(organization_id, name_key)
        );
        CREATE INDEX IF NOT EXISTS idx_projects_org ON projects(organization_id);
        CREATE INDEX IF NOT EXISTS idx_projects_org_status ON projects(organization_id, status);
        ''')
        self.conn.commit()
    @staticmethod
    def _key(name): return name.strip().casefold()
    @staticmethod
    def _row(row):
        if row is None: return None
        return Project(id=UUID(row['id']), organization_id=UUID(row['organization_id']), name=row['name'], status=ProjectStatus(row['status']), created_at=datetime.fromisoformat(row['created_at']), updated_at=datetime.fromisoformat(row['updated_at']), version=row['version'])
    def get_by_id(self, project_id, organization_id=None):
        q='SELECT * FROM projects WHERE id=?'; args=[str(project_id)]
        if organization_id is not None: q += ' AND organization_id=?'; args.append(str(organization_id))
        return self._row(self.conn.execute(q,args).fetchone())
    def list_by_organization(self, organization_id):
        rows=self.conn.execute('SELECT * FROM projects WHERE organization_id=? ORDER BY created_at,id',(str(organization_id),)).fetchall()
        return [self._row(r) for r in rows]
    def exists_by_name(self, organization_id, name, exclude_id=None):
        q='SELECT 1 FROM projects WHERE organization_id=? AND name_key=?'; args=[str(organization_id),self._key(name)]
        if exclude_id is not None: q += ' AND id<>?'; args.append(str(exclude_id))
        return self.conn.execute(q,args).fetchone() is not None
    def save(self, project, expected_version=None):
        project.validate_invariants()
        if self.exists_by_name(project.organization_id, project.name, project.id): raise ProjectDuplicateError('project name already exists in organization')
        existing=self.conn.execute('SELECT version FROM projects WHERE id=?',(str(project.id),)).fetchone()
        try:
            if existing is None:
                if expected_version not in (None,0): raise ProjectConcurrencyError('project does not exist for expected version')
                self.conn.execute('INSERT INTO projects VALUES(?,?,?,?,?,?,?,?)',(str(project.id),str(project.organization_id),project.name,self._key(project.name),project.status.value,project.created_at.isoformat(),project.updated_at.isoformat(),project.version))
            else:
                old=existing['version']
                if expected_version is not None and old != expected_version: raise ProjectConcurrencyError(f'version conflict: expected {expected_version}, actual {old}')
                cur=self.conn.execute('UPDATE projects SET name=?,name_key=?,status=?,updated_at=?,version=? WHERE id=? AND version=?',(project.name,self._key(project.name),project.status.value,project.updated_at.isoformat(),project.version,str(project.id),old))
                if cur.rowcount != 1: raise ProjectConcurrencyError('concurrent project update detected')
            self.conn.commit(); return project
        except sqlite3.IntegrityError as exc:
            self.conn.rollback(); raise ProjectDuplicateError(str(exc)) from exc
    def delete(self, project_id, organization_id=None, expected_version=None):
        q='DELETE FROM projects WHERE id=?'; args=[str(project_id)]
        if organization_id is not None: q+=' AND organization_id=?'; args.append(str(organization_id))
        if expected_version is not None: q+=' AND version=?'; args.append(expected_version)
        cur=self.conn.execute(q,args); self.conn.commit()
        if cur.rowcount != 1: raise ProjectNotFound('project not found or version mismatch')
    def begin(self): self.conn.execute('BEGIN')
    def commit(self): self.conn.commit()
    def rollback(self): self.conn.rollback()
    def close(self): self.conn.close()
