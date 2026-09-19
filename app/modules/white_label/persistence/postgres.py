from __future__ import annotations

import psycopg
from psycopg.rows import dict_row
from uuid import UUID

from app.modules.white_label.domain.models import WhiteLabelConfiguration
from app.modules.white_label.domain.repository import WhiteLabelRepository
from app.shared.domain.errors import BusinessRuleViolation


class PostgreSQLWhiteLabelRepository(WhiteLabelRepository):
    """PostgreSQL persistence for tenant-scoped white-label configuration."""

    def __init__(self, connection: psycopg.Connection) -> None:
        self._connection = connection
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS white_label_configurations (
                    id UUID PRIMARY KEY,
                    tenant_id UUID NOT NULL,
                    organization_id UUID NULL,
                    display_name TEXT NOT NULL,
                    short_name TEXT NOT NULL,
                    description TEXT NOT NULL,
                    logo_url TEXT NULL,
                    favicon_url TEXT NULL,
                    primary_color TEXT NOT NULL,
                    secondary_color TEXT NOT NULL,
                    background_color TEXT NOT NULL,
                    theme_color TEXT NOT NULL,
                    locale TEXT NOT NULL,
                    direction TEXT NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL,
                    updated_at TIMESTAMPTZ NOT NULL,
                    version INTEGER NOT NULL,
                    UNIQUE (tenant_id)
                );

                CREATE INDEX IF NOT EXISTS
                    idx_white_label_configurations_tenant
                    ON white_label_configurations (tenant_id);

                CREATE INDEX IF NOT EXISTS
                    idx_white_label_configurations_organization
                    ON white_label_configurations (organization_id);
                """
            )
        self._connection.commit()

    def get_by_tenant(
        self,
        tenant_id: UUID,
    ) -> WhiteLabelConfiguration | None:
        with self._connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                SELECT *
                FROM white_label_configurations
                WHERE tenant_id = %s
                LIMIT 1
                """,
                (tenant_id,),
            )
            row = cursor.fetchone()

        return None if row is None else self._from_row(row)

    def get_by_id(
        self,
        configuration_id: UUID,
    ) -> WhiteLabelConfiguration | None:
        with self._connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                SELECT *
                FROM white_label_configurations
                WHERE id = %s
                LIMIT 1
                """,
                (configuration_id,),
            )
            row = cursor.fetchone()

        return None if row is None else self._from_row(row)

    def save(
        self,
        configuration: WhiteLabelConfiguration,
    ) -> WhiteLabelConfiguration:
        try:
            with self._connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO white_label_configurations (
                        id,
                        tenant_id,
                        organization_id,
                        display_name,
                        short_name,
                        description,
                        logo_url,
                        favicon_url,
                        primary_color,
                        secondary_color,
                        background_color,
                        theme_color,
                        locale,
                        direction,
                        created_at,
                        updated_at,
                        version
                    )
                    VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s, %s
                    )
                    ON CONFLICT (id) DO UPDATE SET
                        organization_id = EXCLUDED.organization_id,
                        display_name = EXCLUDED.display_name,
                        short_name = EXCLUDED.short_name,
                        description = EXCLUDED.description,
                        logo_url = EXCLUDED.logo_url,
                        favicon_url = EXCLUDED.favicon_url,
                        primary_color = EXCLUDED.primary_color,
                        secondary_color = EXCLUDED.secondary_color,
                        background_color = EXCLUDED.background_color,
                        theme_color = EXCLUDED.theme_color,
                        locale = EXCLUDED.locale,
                        direction = EXCLUDED.direction,
                        created_at = EXCLUDED.created_at,
                        updated_at = EXCLUDED.updated_at,
                        version = EXCLUDED.version
                    WHERE white_label_configurations.tenant_id =
                          EXCLUDED.tenant_id
                    """,
                    (
                        configuration.id,
                        configuration.tenant_id,
                        configuration.organization_id,
                        configuration.display_name,
                        configuration.short_name,
                        configuration.description,
                        configuration.logo_url,
                        configuration.favicon_url,
                        configuration.primary_color,
                        configuration.secondary_color,
                        configuration.background_color,
                        configuration.theme_color,
                        configuration.locale,
                        configuration.direction,
                        configuration.created_at,
                        configuration.updated_at,
                        configuration.version,
                    ),
                )

                if cursor.rowcount == 0:
                    raise BusinessRuleViolation(
                        "white-label configuration belongs to another tenant"
                    )

            self._connection.commit()
        except psycopg.IntegrityError as exc:
            self._connection.rollback()
            raise BusinessRuleViolation(
                "invalid or duplicate white-label configuration"
            ) from exc

        return configuration

    def delete(
        self,
        configuration_id: UUID,
    ) -> None:
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                DELETE FROM white_label_configurations
                WHERE id = %s
                """,
                (configuration_id,),
            )
        self._connection.commit()

    @staticmethod
    def _from_row(row: dict) -> WhiteLabelConfiguration:
        return WhiteLabelConfiguration(
            id=row["id"],
            tenant_id=row["tenant_id"],
            organization_id=row["organization_id"],
            display_name=row["display_name"],
            short_name=row["short_name"],
            description=row["description"],
            logo_url=row["logo_url"],
            favicon_url=row["favicon_url"],
            primary_color=row["primary_color"],
            secondary_color=row["secondary_color"],
            background_color=row["background_color"],
            theme_color=row["theme_color"],
            locale=row["locale"],
            direction=row["direction"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            version=row["version"],
        )
