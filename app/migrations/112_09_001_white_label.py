MIGRATION_ID = "112.09.001"

TABLES = {
    "white_label_configurations": """
        CREATE TABLE IF NOT EXISTS white_label_configurations (
            id TEXT PRIMARY KEY,
            tenant_id TEXT NOT NULL,
            organization_id TEXT NULL,
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
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            version INTEGER NOT NULL,
            UNIQUE(tenant_id)
        )
    """,
}

INDEXES = {
    "idx_white_label_configurations_tenant":
        """
        CREATE INDEX IF NOT EXISTS
        idx_white_label_configurations_tenant
        ON white_label_configurations(tenant_id)
        """,
    "idx_white_label_configurations_organization":
        """
        CREATE INDEX IF NOT EXISTS
        idx_white_label_configurations_organization
        ON white_label_configurations(organization_id)
        """,
}


def apply(connection) -> None:
    for statement in TABLES.values():
        connection.execute(statement)

    for statement in INDEXES.values():
        connection.execute(statement)

    connection.commit()
