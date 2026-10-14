import json
from datetime import datetime
from uuid import UUID

import psycopg

from app.modules.authentication.security import (
    CredentialRecord,
    CredentialStatus,
    PasswordHash,
    Role,
    TokenRecord,
    TokenType,
)


class PostgreSQLCredentialRepository:
    def __init__(self, dsn: str):
        self.dsn = dsn
        self._init_schema()

    def _connect(self):
        return psycopg.connect(self.dsn)

    def _init_schema(self):
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS credentials (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    algorithm TEXT NOT NULL,
                    iterations INTEGER NOT NULL,
                    salt TEXT NOT NULL,
                    digest TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    compromised_at TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS uq_active_credential
                ON credentials(user_id)
                WHERE status = 'active'
                """
            )

    @staticmethod
    def _row(row):
        if row is None:
            return None

        return CredentialRecord(
            UUID(row[0]),
            UUID(row[1]),
            PasswordHash(row[2], row[3], row[4], row[5]),
            CredentialStatus(row[6]),
            datetime.fromisoformat(row[7]),
            datetime.fromisoformat(row[8]),
            row[9],
            datetime.fromisoformat(row[10]) if row[10] else None,
        )

    def active(self, user_id):
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT * FROM credentials
                WHERE user_id=%s AND status='active'
                """,
                (str(user_id),),
            ).fetchone()

        return self._row(row)

    def add(self, credential):
        if self.active(credential.user_id):
            raise ValueError("active credential already exists")

        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO credentials
                    (
                        id,user_id,algorithm,iterations,salt,digest,
                        status,created_at,updated_at,version,compromised_at
                    )
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """,
                (
                    str(credential.id),
                    str(credential.user_id),
                    credential.password_hash.algorithm,
                    credential.password_hash.iterations,
                    credential.password_hash.salt,
                    credential.password_hash.digest,
                    credential.status.value,
                    credential.created_at.isoformat(),
                    credential.updated_at.isoformat(),
                    credential.version,
                    credential.compromised_at.isoformat()
                    if credential.compromised_at
                    else None,
                ),
            )

    def replace(self, credential):
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE credentials
                SET
                    algorithm=%s,
                    iterations=%s,
                    salt=%s,
                    digest=%s,
                    status=%s,
                    updated_at=%s,
                    version=%s,
                    compromised_at=%s
                WHERE id=%s
                """,
                (
                    credential.password_hash.algorithm,
                    credential.password_hash.iterations,
                    credential.password_hash.salt,
                    credential.password_hash.digest,
                    credential.status.value,
                    credential.updated_at.isoformat(),
                    credential.version,
                    credential.compromised_at.isoformat()
                    if credential.compromised_at
                    else None,
                    str(credential.id),
                ),
            )

    def revoke_user(self, user_id, status=CredentialStatus.REVOKED):
        credential = self.active(user_id)

        if not credential:
            return None

        credential.status = status
        credential.version += 1
        credential.updated_at = datetime.now(credential.updated_at.tzinfo)
        self.replace(credential)
        return credential


class PostgreSQLTokenRepository:
    def __init__(self, dsn: str):
        self.dsn = dsn
        self._init_schema()

    def _connect(self):
        return psycopg.connect(self.dsn)

    def _init_schema(self):
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS tokens (
                    token_hash TEXT PRIMARY KEY,
                    token_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    token_type TEXT NOT NULL,
                    issued_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    revoked INTEGER NOT NULL,
                    tenant_id TEXT,
                    roles TEXT NOT NULL
                )
                """
            )

    def put(self, key, record):
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO tokens
                    (
                        token_hash,token_id,user_id,token_type,
                        issued_at,expires_at,session_id,revoked,
                        tenant_id,roles
                    )
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT(token_hash) DO UPDATE SET
                    token_id=EXCLUDED.token_id,
                    user_id=EXCLUDED.user_id,
                    token_type=EXCLUDED.token_type,
                    issued_at=EXCLUDED.issued_at,
                    expires_at=EXCLUDED.expires_at,
                    session_id=EXCLUDED.session_id,
                    revoked=EXCLUDED.revoked,
                    tenant_id=EXCLUDED.tenant_id,
                    roles=EXCLUDED.roles
                """,
                (
                    key,
                    str(record.token_id),
                    str(record.user_id),
                    record.token_type.value,
                    record.issued_at.isoformat(),
                    record.expires_at.isoformat(),
                    str(record.session_id),
                    int(record.revoked),
                    str(record.tenant_id) if record.tenant_id else None,
                    json.dumps(record.roles),
                ),
            )

    def get(self, key):
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM tokens WHERE token_hash=%s",
                (key,),
            ).fetchone()

        if row is None:
            return None

        return TokenRecord(
            UUID(row[1]),
            UUID(row[2]),
            TokenType(row[3]),
            datetime.fromisoformat(row[4]),
            datetime.fromisoformat(row[5]),
            UUID(row[6]),
            bool(row[7]),
            UUID(row[8]) if row[8] else None,
            tuple(json.loads(row[9])),
        )

    def revoke(self, key):
        with self._connect() as conn:
            conn.execute(
                "UPDATE tokens SET revoked=1 WHERE token_hash=%s",
                (key,),
            )

    def revoke_session(self, session_id):
        with self._connect() as conn:
            conn.execute(
                "UPDATE tokens SET revoked=1 WHERE session_id=%s",
                (str(session_id),),
            )
