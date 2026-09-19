from __future__ import annotations

import sqlite3
from datetime import datetime
from threading import RLock
from uuid import UUID

from app.modules.white_label.domain.models import WhiteLabelConfiguration
from app.modules.white_label.domain.repository import WhiteLabelRepository
from app.shared.domain.errors import InvalidDomainData


class SQLiteWhiteLabelRepository(WhiteLabelRepository):
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection
        self._lock = RLock()
        self._connection.row_factory = sqlite3.Row

    def get_by_tenant(
        self,
        tenant_id: UUID,
    ) -> WhiteLabelConfiguration | None:
        with self._lock:
            row = self._connection.execute(
                """
                SELECT *
                FROM white_label_configurations
                WHERE tenant_id = ?
                LIMIT 1
                """,
                (str(tenant_id),),
            ).fetchone()

        return self._to_domain(row) if row else None

    def get_by_id(
        self,
        configuration_id: UUID,
    ) -> WhiteLabelConfiguration | None:
        with self._lock:
            row = self._connection.execute(
                """
                SELECT *
                FROM white_label_configurations
                WHERE id = ?
                LIMIT 1
                """,
                (str(configuration_id),),
            ).fetchone()

        return self._to_domain(row) if row else None

    def save(
        self,
        configuration: WhiteLabelConfiguration,
    ) -> WhiteLabelConfiguration:
        with self._lock:
            self._connection.execute(
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
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    tenant_id = excluded.tenant_id,
                    organization_id = excluded.organization_id,
                    display_name = excluded.display_name,
                    short_name = excluded.short_name,
                    description = excluded.description,
                    logo_url = excluded.logo_url,
                    favicon_url = excluded.favicon_url,
                    primary_color = excluded.primary_color,
                    secondary_color = excluded.secondary_color,
                    background_color = excluded.background_color,
                    theme_color = excluded.theme_color,
                    locale = excluded.locale,
                    direction = excluded.direction,
                    updated_at = excluded.updated_at,
                    version = excluded.version
                """,
                (
                    str(configuration.id),
                    str(configuration.tenant_id),
                    (
                        str(configuration.organization_id)
                        if configuration.organization_id is not None
                        else None
                    ),
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
                    configuration.created_at.isoformat(),
                    configuration.updated_at.isoformat(),
                    configuration.version,
                ),
            )
            self._connection.commit()

        return configuration

    def delete(self, configuration_id: UUID) -> None:
        with self._lock:
            self._connection.execute(
                """
                DELETE FROM white_label_configurations
                WHERE id = ?
                """,
                (str(configuration_id),),
            )
            self._connection.commit()

    @staticmethod
    def _to_domain(row: sqlite3.Row) -> WhiteLabelConfiguration:
        try:
            return WhiteLabelConfiguration(
                id=UUID(row["id"]),
                tenant_id=UUID(row["tenant_id"]),
                organization_id=(
                    UUID(row["organization_id"])
                    if row["organization_id"]
                    else None
                ),
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
                created_at=datetime.fromisoformat(
                    row["created_at"]
                ),
                updated_at=datetime.fromisoformat(
                    row["updated_at"]
                ),
                version=int(row["version"]),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise InvalidDomainData(
                "Stored white-label configuration is invalid"
            ) from exc
