from __future__ import annotations

import sqlite3
from threading import RLock
from uuid import UUID

from app.shared.domain.errors import BusinessRuleViolation
from .mappers import (
    application_from_row,
    application_to_row,
    credential_from_row,
    credential_to_row,
    listing_from_row,
    listing_to_row,
)
from .repository import DeveloperRepository
from ..domain.models import (
    DeveloperApplication,
    DeveloperCredential,
    MarketplaceListing,
)


def _serialized(method):
    def wrapper(self, *args, **kwargs):
        with self._lock:
            return method(self, *args, **kwargs)

    wrapper.__name__ = method.__name__
    wrapper.__doc__ = method.__doc__
    wrapper.__module__ = method.__module__
    return wrapper


class SQLiteDeveloperRepository(DeveloperRepository):
    """SQLite persistence for tenant-scoped developer resources."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection
        self._lock = RLock()
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self._ensure_schema()

    @_serialized
    def _ensure_schema(self) -> None:
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS developer_applications (
                id TEXT NOT NULL,
                tenant_id TEXT NOT NULL,
                name TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                version INTEGER NOT NULL,
                PRIMARY KEY (id),
                UNIQUE (tenant_id, id)
            );

            CREATE TABLE IF NOT EXISTS developer_credentials (
                id TEXT NOT NULL,
                tenant_id TEXT NOT NULL,
                application_id TEXT NOT NULL,
                client_id TEXT NOT NULL,
                secret_hash TEXT NOT NULL,
                scopes TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT,
                revoked_at TEXT,
                version INTEGER NOT NULL,
                PRIMARY KEY (id),
                UNIQUE (tenant_id, client_id),
                UNIQUE (tenant_id, id),
                FOREIGN KEY (tenant_id, application_id)
                    REFERENCES developer_applications (tenant_id, id)
                    ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS developer_listings (
                id TEXT NOT NULL,
                tenant_id TEXT NOT NULL,
                publisher_application_id TEXT NOT NULL,
                name TEXT NOT NULL,
                description TEXT NOT NULL,
                capability TEXT NOT NULL,
                published INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                version INTEGER NOT NULL,
                PRIMARY KEY (id),
                UNIQUE (tenant_id, id),
                FOREIGN KEY (tenant_id, publisher_application_id)
                    REFERENCES developer_applications (tenant_id, id)
                    ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_developer_applications_tenant
                ON developer_applications (tenant_id);

            CREATE INDEX IF NOT EXISTS idx_developer_credentials_tenant
                ON developer_credentials (tenant_id);

            CREATE INDEX IF NOT EXISTS idx_developer_credentials_application
                ON developer_credentials (tenant_id, application_id);

            CREATE INDEX IF NOT EXISTS idx_developer_listings_tenant
                ON developer_listings (tenant_id);
            """
        )
        self.connection.commit()

    @_serialized
    def save_application(
        self,
        application: DeveloperApplication,
    ) -> DeveloperApplication:
        row = application_to_row(application)

        self.connection.execute(
            """
            INSERT INTO developer_applications (
                id,
                tenant_id,
                name,
                status,
                created_at,
                updated_at,
                version
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                name = excluded.name,
                status = excluded.status,
                updated_at = excluded.updated_at,
                version = excluded.version
            WHERE developer_applications.tenant_id = excluded.tenant_id
            """,
            row,
        )
        if self.connection.execute(
            "SELECT tenant_id FROM developer_applications WHERE id = ?",
            (row[0],),
        ).fetchone()["tenant_id"] != row[1]:
            self.connection.rollback()
            raise BusinessRuleViolation("developer application belongs to another tenant")
        self.connection.commit()
        return application

    @_serialized
    def get_application(
        self,
        tenant_id: UUID,
        application_id: UUID,
    ) -> DeveloperApplication | None:
        row = self.connection.execute(
            """
            SELECT *
            FROM developer_applications
            WHERE tenant_id = ? AND id = ?
            """,
            (str(tenant_id), str(application_id)),
        ).fetchone()

        return application_from_row(row) if row is not None else None

    @_serialized
    def list_applications(
        self,
        tenant_id: UUID,
    ) -> tuple[DeveloperApplication, ...]:
        rows = self.connection.execute(
            """
            SELECT *
            FROM developer_applications
            WHERE tenant_id = ?
            ORDER BY created_at, id
            """,
            (str(tenant_id),),
        ).fetchall()

        return tuple(application_from_row(row) for row in rows)

    @_serialized
    def delete_application(
        self,
        tenant_id: UUID,
        application_id: UUID,
    ) -> None:
        self.connection.execute(
            """
            DELETE FROM developer_applications
            WHERE tenant_id = ? AND id = ?
            """,
            (str(tenant_id), str(application_id)),
        )
        self.connection.commit()

    @_serialized
    def save_credential(
        self,
        credential: DeveloperCredential,
    ) -> DeveloperCredential:
        row = credential_to_row(credential)

        self.connection.execute(
            """
            INSERT INTO developer_credentials (
                id,
                tenant_id,
                application_id,
                client_id,
                secret_hash,
                scopes,
                status,
                created_at,
                expires_at,
                revoked_at,
                version
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                application_id = excluded.application_id,
                client_id = excluded.client_id,
                secret_hash = excluded.secret_hash,
                scopes = excluded.scopes,
                status = excluded.status,
                created_at = excluded.created_at,
                expires_at = excluded.expires_at,
                revoked_at = excluded.revoked_at,
                version = excluded.version
            WHERE developer_credentials.tenant_id = excluded.tenant_id
            """,
            row,
        )
        existing = self.connection.execute(
            "SELECT tenant_id FROM developer_credentials WHERE id = ?",
            (row[0],),
        ).fetchone()
        if existing is not None and existing["tenant_id"] != row[1]:
            self.connection.rollback()
            raise BusinessRuleViolation("developer credential belongs to another tenant")
        self.connection.commit()
        return credential

    @_serialized
    def get_credential(
        self,
        tenant_id: UUID,
        credential_id: UUID,
    ) -> DeveloperCredential | None:
        row = self.connection.execute(
            """
            SELECT *
            FROM developer_credentials
            WHERE tenant_id = ? AND id = ?
            """,
            (str(tenant_id), str(credential_id)),
        ).fetchone()

        return credential_from_row(row) if row is not None else None

    @_serialized
    def get_credential_by_client_id(
        self,
        tenant_id: UUID,
        client_id: str,
    ) -> DeveloperCredential | None:
        row = self.connection.execute(
            "SELECT * FROM developer_credentials "
            "WHERE tenant_id = ? AND client_id = ?",
            (str(tenant_id), client_id.strip()),
        ).fetchone()
        return credential_from_row(row) if row is not None else None

    @_serialized
    def list_credentials(
        self,
        tenant_id: UUID,
        *,
        application_id: UUID | None = None,
    ) -> tuple[DeveloperCredential, ...]:
        if application_id is None:
            rows = self.connection.execute(
                """
                SELECT *
                FROM developer_credentials
                WHERE tenant_id = ?
                ORDER BY created_at, id
                """,
                (str(tenant_id),),
            ).fetchall()
        else:
            rows = self.connection.execute(
                """
                SELECT *
                FROM developer_credentials
                WHERE tenant_id = ? AND application_id = ?
                ORDER BY created_at, id
                """,
                (str(tenant_id), str(application_id)),
            ).fetchall()

        return tuple(credential_from_row(row) for row in rows)

    @_serialized
    def delete_credential(
        self,
        tenant_id: UUID,
        credential_id: UUID,
    ) -> None:
        self.connection.execute(
            """
            DELETE FROM developer_credentials
            WHERE tenant_id = ? AND id = ?
            """,
            (str(tenant_id), str(credential_id)),
        )
        self.connection.commit()

    @_serialized
    def save_listing(
        self,
        listing: MarketplaceListing,
    ) -> MarketplaceListing:
        row = listing_to_row(listing)

        self.connection.execute(
            """
            INSERT INTO developer_listings (
                id,
                tenant_id,
                publisher_application_id,
                name,
                description,
                capability,
                published,
                created_at,
                updated_at,
                version
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                publisher_application_id = excluded.publisher_application_id,
                name = excluded.name,
                description = excluded.description,
                capability = excluded.capability,
                published = excluded.published,
                created_at = excluded.created_at,
                updated_at = excluded.updated_at,
                version = excluded.version
            WHERE developer_listings.tenant_id = excluded.tenant_id
            """,
            row,
        )
        existing = self.connection.execute(
            "SELECT tenant_id FROM developer_listings WHERE id = ?",
            (row[0],),
        ).fetchone()
        if existing is not None and existing["tenant_id"] != row[1]:
            self.connection.rollback()
            raise BusinessRuleViolation("marketplace listing belongs to another tenant")
        self.connection.commit()
        return listing

    @_serialized
    def get_listing(
        self,
        tenant_id: UUID,
        listing_id: UUID,
    ) -> MarketplaceListing | None:
        row = self.connection.execute(
            """
            SELECT *
            FROM developer_listings
            WHERE tenant_id = ? AND id = ?
            """,
            (str(tenant_id), str(listing_id)),
        ).fetchone()

        return listing_from_row(row) if row is not None else None

    @_serialized
    def list_listings(
        self,
        tenant_id: UUID,
    ) -> tuple[MarketplaceListing, ...]:
        rows = self.connection.execute(
            """
            SELECT *
            FROM developer_listings
            WHERE tenant_id = ?
            ORDER BY created_at, id
            """,
            (str(tenant_id),),
        ).fetchall()

        return tuple(listing_from_row(row) for row in rows)

    @_serialized
    def delete_listing(
        self,
        tenant_id: UUID,
        listing_id: UUID,
    ) -> None:
        self.connection.execute(
            """
            DELETE FROM developer_listings
            WHERE tenant_id = ? AND id = ?
            """,
            (str(tenant_id), str(listing_id)),
        )
        self.connection.commit()
