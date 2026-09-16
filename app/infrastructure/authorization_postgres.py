import json

import psycopg


class PostgreSQLRBAC:
    def __init__(self, dsn: str):
        self.dsn = dsn
        self._init_schema()

    def _connect(self):
        return psycopg.connect(self.dsn)

    def _init_schema(self):
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS roles (
                    name TEXT PRIMARY KEY,
                    permissions TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS role_assignments (
                    user_id TEXT NOT NULL,
                    tenant_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    PRIMARY KEY(user_id, tenant_id, role),
                    FOREIGN KEY(role) REFERENCES roles(name)
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_role_assignments_scope
                ON role_assignments(user_id, tenant_id)
                """
            )

    def define(self, role, permissions):
        payload = json.dumps(sorted(set(permissions)))

        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO roles(name, permissions)
                VALUES (%s, %s)
                ON CONFLICT(name) DO UPDATE
                SET permissions=EXCLUDED.permissions
                """,
                (role, payload),
            )

    def assign(self, user_id, role, tenant_id):
        with self._connect() as conn:
            if not conn.execute(
                "SELECT 1 FROM roles WHERE name=%s",
                (role,),
            ).fetchone():
                raise ValueError("unknown role")

            conn.execute(
                """
                INSERT INTO role_assignments(user_id, tenant_id, role)
                VALUES (%s, %s, %s)
                ON CONFLICT(user_id, tenant_id, role) DO NOTHING
                """,
                (str(user_id), str(tenant_id), role),
            )

    def permissions(self, user_id, tenant_id):
        result = set()

        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT r.permissions
                FROM role_assignments a
                JOIN roles r ON r.name=a.role
                WHERE a.user_id=%s AND a.tenant_id=%s
                """,
                (str(user_id), str(tenant_id)),
            ).fetchall()

        for (payload,) in rows:
            result.update(json.loads(payload))

        return frozenset(result)

    def require(self, user_id, tenant_id, permission):
        if permission not in self.permissions(user_id, tenant_id):
            raise PermissionError("permission denied")
