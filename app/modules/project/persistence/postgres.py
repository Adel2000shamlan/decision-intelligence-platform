from __future__ import annotations

from datetime import datetime
from uuid import UUID

import psycopg

from app.modules.project.domain.models import Project, ProjectStatus


class ProjectRepositoryError(Exception):
    pass


class ProjectNotFound(ProjectRepositoryError):
    pass


class ProjectConcurrencyError(ProjectRepositoryError):
    pass


class ProjectDuplicateError(ProjectRepositoryError):
    pass


class PostgreSQLProjectRepository:
    """Durable PostgreSQL Project repository with optimistic concurrency."""

    def __init__(self, dsn: str):
        self.dsn = dsn
        self._init_schema()

    def _connect(self):
        return psycopg.connect(self.dsn)

    def _init_schema(self):
        with self._connect() as conn:
            conn.execute(
                """
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
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_projects_org
                ON projects(organization_id)
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_projects_org_status
                ON projects(organization_id, status)
                """
            )

    @staticmethod
    def _key(name):
        return name.strip().casefold()

    @staticmethod
    def _row(row):
        if row is None:
            return None

        return Project(
            id=UUID(row[0]),
            organization_id=UUID(row[1]),
            name=row[2],
            status=ProjectStatus(row[4]),
            created_at=datetime.fromisoformat(row[5]),
            updated_at=datetime.fromisoformat(row[6]),
            version=row[7],
        )

    def get_by_id(self, project_id, organization_id=None):
        query = "SELECT * FROM projects WHERE id=%s"
        args = [str(project_id)]

        if organization_id is not None:
            query += " AND organization_id=%s"
            args.append(str(organization_id))

        with self._connect() as conn:
            row = conn.execute(query, args).fetchone()

        return self._row(row)

    def list_by_organization(self, organization_id):
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM projects
                WHERE organization_id=%s
                ORDER BY created_at, id
                """,
                (str(organization_id),),
            ).fetchall()

        return [self._row(row) for row in rows]

    def exists_by_name(self, organization_id, name, exclude_id=None):
        query = """
            SELECT 1 FROM projects
            WHERE organization_id=%s AND name_key=%s
        """
        args = [str(organization_id), self._key(name)]

        if exclude_id is not None:
            query += " AND id<>%s"
            args.append(str(exclude_id))

        with self._connect() as conn:
            return conn.execute(query, args).fetchone() is not None

    def save(self, project, expected_version=None):
        project.validate_invariants()

        if self.exists_by_name(
            project.organization_id,
            project.name,
            project.id,
        ):
            raise ProjectDuplicateError(
                "project name already exists in organization"
            )

        try:
            with self._connect() as conn:
                existing = conn.execute(
                    "SELECT organization_id, version FROM projects WHERE id=%s FOR UPDATE",
                    (str(project.id),),
                ).fetchone()

                if existing is None:
                    if expected_version not in (None, 0):
                        raise ProjectConcurrencyError(
                            "project does not exist for expected version"
                        )

                    conn.execute(
                        """
                        INSERT INTO projects
                            (
                                id,
                                organization_id,
                                name,
                                name_key,
                                status,
                                created_at,
                                updated_at,
                                version
                            )
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                        """,
                        (
                            str(project.id),
                            str(project.organization_id),
                            project.name,
                            self._key(project.name),
                            project.status.value,
                            project.created_at.isoformat(),
                            project.updated_at.isoformat(),
                            project.version,
                        ),
                    )
                else:
                    if existing[0] != str(project.organization_id):
                        raise ProjectNotFound(
                            "project not found for organization"
                        )

                    old = existing[1]

                    if expected_version is not None and old != expected_version:
                        raise ProjectConcurrencyError(
                            f"version conflict: expected {expected_version}, actual {old}"
                        )

                    cur = conn.execute(
                        """
                        UPDATE projects
                        SET
                            name=%s,
                            name_key=%s,
                            status=%s,
                            updated_at=%s,
                            version=%s
                        WHERE id=%s AND version=%s
                        """,
                        (
                            project.name,
                            self._key(project.name),
                            project.status.value,
                            project.updated_at.isoformat(),
                            project.version,
                            str(project.id),
                            old,
                        ),
                    )

                    if cur.rowcount != 1:
                        raise ProjectConcurrencyError(
                            "concurrent project update detected"
                        )

            return project

        except psycopg.errors.UniqueViolation as exc:
            raise ProjectDuplicateError(str(exc)) from exc

    def delete(self, project_id, organization_id=None, expected_version=None):
        query = "DELETE FROM projects WHERE id=%s"
        args = [str(project_id)]

        if organization_id is not None:
            query += " AND organization_id=%s"
            args.append(str(organization_id))

        if expected_version is not None:
            query += " AND version=%s"
            args.append(expected_version)

        with self._connect() as conn:
            cur = conn.execute(query, args)

        if cur.rowcount != 1:
            raise ProjectNotFound(
                "project not found or version mismatch"
            )

    def close(self):
        """Compatibility no-op; connections are scoped per operation."""
        return None
