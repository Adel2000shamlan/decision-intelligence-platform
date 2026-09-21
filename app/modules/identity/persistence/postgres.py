from datetime import datetime
from uuid import UUID

import psycopg

from app.modules.identity.domain.models import User, UserStatus
from app.modules.identity.domain.repository import UserRepository
from app.shared.domain.errors import BusinessRuleViolation


class PostgreSQLUserRepository(UserRepository):
    def __init__(self, dsn: str):
        self.dsn = dsn
        self._init_schema()

    def _connect(self):
        return psycopg.connect(self.dsn)

    def _init_schema(self):
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    email TEXT NOT NULL UNIQUE,
                    display_name TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    version INTEGER NOT NULL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_users_status ON users(status)"
            )

    @staticmethod
    def _row(row):
        if row is None:
            return None

        return User(
            id=UUID(row[0]),
            email=row[1],
            display_name=row[2],
            description=row[3],
            status=UserStatus(row[4]),
            created_at=datetime.fromisoformat(row[5]),
            updated_at=datetime.fromisoformat(row[6]),
            version=row[7],
        )

    def get_by_id(self, user_id: UUID) -> User | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM users WHERE id=%s",
                (str(user_id),),
            ).fetchone()
        return self._row(row)

    def get_by_email(self, email: str) -> User | None:
        normalized = email.strip().lower()

        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM users WHERE email=%s",
                (normalized,),
            ).fetchone()

        return self._row(row)

    def exists_by_email(self, email: str) -> bool:
        return self.get_by_email(email) is not None

    def save(self, user: User) -> User:
        user.validate_invariants()

        with self._connect() as conn:
            existing = conn.execute(
                "SELECT version FROM users WHERE id=%s",
                (str(user.id),),
            ).fetchone()

            if existing is None:
                if user.version != 1:
                    raise BusinessRuleViolation(
                        "new user must start at version 1"
                    )

                try:
                    conn.execute(
                        """
                        INSERT INTO users
                            (
                                id,
                                email,
                                display_name,
                                description,
                                status,
                                created_at,
                                updated_at,
                                version
                            )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            str(user.id),
                            user.email_address,
                            user.name,
                            user.description.value,
                            user.status.value,
                            user.created_at.isoformat(),
                            user.updated_at.isoformat(),
                            user.version,
                        ),
                    )
                except psycopg.errors.UniqueViolation as exc:
                    raise BusinessRuleViolation(
                        "user email already exists"
                    ) from exc

                return user

            existing_version = existing[0]

            if existing_version == user.version:
                raise BusinessRuleViolation(
                    f"user version {user.version} already exists"
                )

            expected_previous_version = user.version - 1

            if existing_version != expected_previous_version:
                raise BusinessRuleViolation(
                    "user concurrency conflict: "
                    f"version {expected_previous_version}, "
                    f"found {existing_version}"
                )

            try:
                updated = conn.execute(
                    """
                    UPDATE users
                    SET
                        email = %s,
                        display_name = %s,
                        description = %s,
                        status = %s,
                        created_at = %s,
                        updated_at = %s,
                        version = %s
                    WHERE id = %s
                      AND version = %s
                    """,
                    (
                        user.email_address,
                        user.name,
                        user.description.value,
                        user.status.value,
                        user.created_at.isoformat(),
                        user.updated_at.isoformat(),
                        user.version,
                        str(user.id),
                        expected_previous_version,
                    ),
                )
            except psycopg.errors.UniqueViolation as exc:
                raise BusinessRuleViolation(
                    "user email already exists"
                ) from exc

            if updated.rowcount != 1:
                raise BusinessRuleViolation(
                    "user concurrency conflict: "
                    f"version {expected_previous_version}"
                )

        return user
