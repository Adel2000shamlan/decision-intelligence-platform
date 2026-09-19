from __future__ import annotations

import psycopg
from psycopg.rows import dict_row
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


class PostgresDeveloperRepository(DeveloperRepository):
    """PostgreSQL persistence for tenant-scoped developer resources."""

    def __init__(self, connection: psycopg.Connection) -> None:
        self._connection = connection
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS developer_applications (
                    id UUID PRIMARY KEY,
                    tenant_id UUID NOT NULL,
                    name TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL,
                    updated_at TIMESTAMPTZ NOT NULL,
                    version INTEGER NOT NULL,
                    UNIQUE (tenant_id, id)
                );

                CREATE TABLE IF NOT EXISTS developer_credentials (
                    id UUID PRIMARY KEY,
                    tenant_id UUID NOT NULL,
                    application_id UUID NOT NULL,
                    client_id TEXT NOT NULL,
                    secret_hash TEXT NOT NULL,
                    scopes TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL,
                    expires_at TIMESTAMPTZ,
                    revoked_at TIMESTAMPTZ,
                    version INTEGER NOT NULL,
                    UNIQUE (tenant_id, client_id),
                    UNIQUE (tenant_id, id),
                    FOREIGN KEY (tenant_id, application_id)
                        REFERENCES developer_applications (tenant_id, id)
                        ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS developer_listings (
                    id UUID PRIMARY KEY,
                    tenant_id UUID NOT NULL,
                    publisher_application_id UUID NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT NOT NULL,
                    capability TEXT NOT NULL,
                    published BOOLEAN NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL,
                    updated_at TIMESTAMPTZ NOT NULL,
                    version INTEGER NOT NULL,
                    UNIQUE (tenant_id, id),
                    FOREIGN KEY (tenant_id, publisher_application_id)
                        REFERENCES developer_applications (tenant_id, id)
                        ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS
                    idx_developer_applications_tenant
                    ON developer_applications (tenant_id);

                CREATE INDEX IF NOT EXISTS
                    idx_developer_credentials_tenant
                    ON developer_credentials (tenant_id);

                CREATE INDEX IF NOT EXISTS
                    idx_developer_credentials_application
                    ON developer_credentials (tenant_id, application_id);

                CREATE INDEX IF NOT EXISTS
                    idx_developer_listings_tenant
                    ON developer_listings (tenant_id);
                """
            )

        self._connection.commit()

    def save_application(
        self,
        application: DeveloperApplication,
    ) -> DeveloperApplication:
        try:
            with self._connection.cursor() as cursor:
                cursor.execute(
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
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO UPDATE SET
                        name = EXCLUDED.name,
                        status = EXCLUDED.status,
                        updated_at = EXCLUDED.updated_at,
                        version = EXCLUDED.version
                    WHERE developer_applications.tenant_id = EXCLUDED.tenant_id
                    """,
                    application_to_row(application),
                )
                if cursor.rowcount == 0:
                    raise BusinessRuleViolation(
                        "developer application belongs to another tenant"
                    )
            self._connection.commit()
        except psycopg.IntegrityError as exc:
            self._connection.rollback()
            raise BusinessRuleViolation(
                "duplicate developer application"
            ) from exc

        return application

    def get_application(
        self,
        tenant_id: UUID,
        application_id: UUID,
    ) -> DeveloperApplication | None:
        with self._connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                SELECT *
                FROM developer_applications
                WHERE tenant_id = %s AND id = %s
                """,
                (tenant_id, application_id),
            )
            row = cursor.fetchone()

        return None if row is None else application_from_row(row)

    def list_applications(
        self,
        tenant_id: UUID,
    ) -> tuple[DeveloperApplication, ...]:
        with self._connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                SELECT *
                FROM developer_applications
                WHERE tenant_id = %s
                ORDER BY created_at, id
                """,
                (tenant_id,),
            )
            rows = cursor.fetchall()

        return tuple(application_from_row(row) for row in rows)

    def delete_application(
        self,
        tenant_id: UUID,
        application_id: UUID,
    ) -> None:
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                DELETE FROM developer_applications
                WHERE tenant_id = %s AND id = %s
                """,
                (tenant_id, application_id),
            )
        self._connection.commit()

    def save_credential(
        self,
        credential: DeveloperCredential,
    ) -> DeveloperCredential:
        try:
            with self._connection.cursor() as cursor:
                cursor.execute(
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
                    VALUES (
                        %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s
                    )
                    ON CONFLICT (id) DO UPDATE SET
                        application_id = EXCLUDED.application_id,
                        client_id = EXCLUDED.client_id,
                        secret_hash = EXCLUDED.secret_hash,
                        scopes = EXCLUDED.scopes,
                        status = EXCLUDED.status,
                        created_at = EXCLUDED.created_at,
                        expires_at = EXCLUDED.expires_at,
                        revoked_at = EXCLUDED.revoked_at,
                        version = EXCLUDED.version
                    WHERE developer_credentials.tenant_id = EXCLUDED.tenant_id
                    """,
                    credential_to_row(credential),
                )
                if cursor.rowcount == 0:
                    raise BusinessRuleViolation(
                        "developer credential belongs to another tenant"
                    )
            self._connection.commit()
        except psycopg.IntegrityError as exc:
            self._connection.rollback()
            raise BusinessRuleViolation(
                "invalid or duplicate developer credential"
            ) from exc

        return credential

    def get_credential(
        self,
        tenant_id: UUID,
        credential_id: UUID,
    ) -> DeveloperCredential | None:
        with self._connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                SELECT *
                FROM developer_credentials
                WHERE tenant_id = %s AND id = %s
                """,
                (tenant_id, credential_id),
            )
            row = cursor.fetchone()

        return None if row is None else credential_from_row(row)

    def get_credential_by_client_id(
        self,
        tenant_id: UUID,
        client_id: str,
    ) -> DeveloperCredential | None:
        with self._connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                "SELECT * FROM developer_credentials "
                "WHERE tenant_id = %s AND client_id = %s",
                (tenant_id, client_id.strip()),
            )
            row = cursor.fetchone()
        return None if row is None else credential_from_row(row)

    def list_credentials(
        self,
        tenant_id: UUID,
        *,
        application_id: UUID | None = None,
    ) -> tuple[DeveloperCredential, ...]:
        with self._connection.cursor(row_factory=dict_row) as cursor:
            if application_id is None:
                cursor.execute(
                    """
                    SELECT *
                    FROM developer_credentials
                    WHERE tenant_id = %s
                    ORDER BY created_at, id
                    """,
                    (tenant_id,),
                )
            else:
                cursor.execute(
                    """
                    SELECT *
                    FROM developer_credentials
                    WHERE tenant_id = %s
                      AND application_id = %s
                    ORDER BY created_at, id
                    """,
                    (tenant_id, application_id),
                )

            rows = cursor.fetchall()

        return tuple(credential_from_row(row) for row in rows)

    def delete_credential(
        self,
        tenant_id: UUID,
        credential_id: UUID,
    ) -> None:
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                DELETE FROM developer_credentials
                WHERE tenant_id = %s AND id = %s
                """,
                (tenant_id, credential_id),
            )
        self._connection.commit()

    def save_listing(
        self,
        listing: MarketplaceListing,
    ) -> MarketplaceListing:
        try:
            with self._connection.cursor() as cursor:
                cursor.execute(
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
                    VALUES (
                        %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s
                    )
                    ON CONFLICT (id) DO UPDATE SET
                        publisher_application_id = EXCLUDED.publisher_application_id,
                        name = EXCLUDED.name,
                        description = EXCLUDED.description,
                        capability = EXCLUDED.capability,
                        published = EXCLUDED.published,
                        created_at = EXCLUDED.created_at,
                        updated_at = EXCLUDED.updated_at,
                        version = EXCLUDED.version
                    WHERE developer_listings.tenant_id = EXCLUDED.tenant_id
                    """,
                    listing_to_row(listing),
                )
                if cursor.rowcount == 0:
                    raise BusinessRuleViolation(
                        "marketplace listing belongs to another tenant"
                    )
            self._connection.commit()
        except psycopg.IntegrityError as exc:
            self._connection.rollback()
            raise BusinessRuleViolation(
                "invalid or duplicate marketplace listing"
            ) from exc

        return listing

    def get_listing(
        self,
        tenant_id: UUID,
        listing_id: UUID,
    ) -> MarketplaceListing | None:
        with self._connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                SELECT *
                FROM developer_listings
                WHERE tenant_id = %s AND id = %s
                """,
                (tenant_id, listing_id),
            )
            row = cursor.fetchone()

        return None if row is None else listing_from_row(row)

    def list_listings(
        self,
        tenant_id: UUID,
    ) -> tuple[MarketplaceListing, ...]:
        with self._connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                SELECT *
                FROM developer_listings
                WHERE tenant_id = %s
                ORDER BY created_at, id
                """,
                (tenant_id,),
            )
            rows = cursor.fetchall()

        return tuple(listing_from_row(row) for row in rows)

    def delete_listing(
        self,
        tenant_id: UUID,
        listing_id: UUID,
    ) -> None:
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                DELETE FROM developer_listings
                WHERE tenant_id = %s AND id = %s
                """,
                (tenant_id, listing_id),
            )
        self._connection.commit()
