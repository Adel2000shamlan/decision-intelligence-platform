from __future__ import annotations

import sqlite3

from app.infrastructure.config import settings
from app.modules.developer.persistence.repository import DeveloperRepository


def create_developer_repository(
    connection: sqlite3.Connection,
) -> DeveloperRepository:
    if settings.database_url.startswith(("postgresql://", "postgres://")):
        from app.modules.developer.persistence.postgres import (
            PostgresDeveloperRepository,
        )

        return PostgresDeveloperRepository(connection)

    from app.modules.developer.persistence.sqlite import (
        SQLiteDeveloperRepository,
    )

    return SQLiteDeveloperRepository(connection)
