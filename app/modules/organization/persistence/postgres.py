from datetime import datetime
from uuid import UUID

import psycopg

from app.modules.organization.domain.models import Organization, OrganizationStatus


class PostgreSQLOrganizationRepository:
    def __init__(self, dsn: str):
        self.dsn = dsn
        self._init_schema()

    def _connect(self):
        return psycopg.connect(self.dsn)

    def _init_schema(self):
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS organizations (
                    id TEXT PRIMARY KEY,
                    tenant_id TEXT,
                    name TEXT NOT NULL,
                    slug TEXT NOT NULL UNIQUE,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    version INTEGER NOT NULL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_org_tenant ON organizations(tenant_id)"
            )

    @staticmethod
    def _row(row):
        if row is None:
            return None
        return Organization(
            id=UUID(row[0]),
            name=row[2],
            slug=row[3],
            status=OrganizationStatus(row[4]),
            created_at=datetime.fromisoformat(row[5]),
            updated_at=datetime.fromisoformat(row[6]),
            version=row[7],
        )

    def save(self, organization, tenant_id=None):
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO organizations
                    (id, tenant_id, name, slug, status, created_at, updated_at, version)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT(id) DO UPDATE SET
                    tenant_id=EXCLUDED.tenant_id,
                    name=EXCLUDED.name,
                    slug=EXCLUDED.slug,
                    status=EXCLUDED.status,
                    updated_at=EXCLUDED.updated_at,
                    version=EXCLUDED.version
                """,
                (
                    str(organization.id),
                    str(tenant_id) if tenant_id else None,
                    organization.name,
                    organization.slug,
                    organization.status.value,
                    organization.created_at.isoformat(),
                    organization.updated_at.isoformat(),
                    organization.version,
                ),
            )
        return organization

    def get_by_id(self, organization_id):
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM organizations WHERE id=%s",
                (str(organization_id),),
            ).fetchone()
        return self._row(row)

    def get_by_slug(self, slug):
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM organizations WHERE slug=%s",
                (slug.strip().lower(),),
            ).fetchone()
        return self._row(row)

    def exists_by_slug(self, slug):
        return self.get_by_slug(slug) is not None

    def list(self, tenant_id=None):
        with self._connect() as conn:
            if tenant_id is None:
                rows = conn.execute(
                    "SELECT * FROM organizations ORDER BY created_at, id"
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM organizations WHERE tenant_id=%s ORDER BY created_at, id",
                    (str(tenant_id),),
                ).fetchall()
        return [self._row(row) for row in rows]
