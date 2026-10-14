from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from app.modules.developer.domain.models import (
    APIScope,
    DeveloperCredential,
    DeveloperCredentialStatus,
)
from app.modules.developer.security.secrets import DeveloperSecretHasher


@dataclass(frozen=True)
class IssuedDeveloperCredential:
    credential: DeveloperCredential
    secret: str


class DeveloperCredentialSecurityService:
    """
    Handles Developer API credential creation, rotation and verification.

    Raw secrets are returned only as part of creation/rotation results.
    The credential itself stores only an encoded password hash.
    """

    def __init__(
        self,
        secret_hasher: DeveloperSecretHasher | None = None,
    ) -> None:
        self.secret_hasher = secret_hasher or DeveloperSecretHasher()

    def issue(
        self,
        *,
        tenant_id: UUID,
        application_id: UUID,
        client_id: str,
        scopes: tuple[APIScope, ...] = (),
        expires_at: datetime | None = None,
    ) -> IssuedDeveloperCredential:
        generated = self.secret_hasher.generate()

        credential = DeveloperCredential.create(
            tenant_id=tenant_id,
            application_id=application_id,
            client_id=client_id,
            secret_hash=self.secret_hasher.encode(generated.hash),
            scopes=scopes,
            expires_at=expires_at,
        )

        return IssuedDeveloperCredential(
            credential=credential,
            secret=generated.raw,
        )

    def verify(
        self,
        credential: DeveloperCredential,
        secret: str,
        *,
        now: datetime | None = None,
    ) -> bool:
        if credential.status is not DeveloperCredentialStatus.ACTIVE:
            return False

        current = now or datetime.now(timezone.utc)

        if current.tzinfo is None:
            raise ValueError("now must be timezone-aware")

        if credential.is_expired(current):
            return False

        stored = self.secret_hasher.decode(credential.secret_hash)
        return self.secret_hasher.verify(secret, stored)

    def rotate(
        self,
        credential: DeveloperCredential,
        *,
        scopes: tuple[APIScope, ...] | None = None,
        expires_at: datetime | None = None,
    ) -> IssuedDeveloperCredential:
        if credential.status is not DeveloperCredentialStatus.ACTIVE:
            raise ValueError("only active credentials can be rotated")

        generated = self.secret_hasher.generate()

        rotated = DeveloperCredential(
            id=credential.id,
            tenant_id=credential.tenant_id,
            application_id=credential.application_id,
            client_id=credential.client_id,
            secret_hash=self.secret_hasher.encode(generated.hash),
            scopes=credential.scopes if scopes is None else scopes,
            status=DeveloperCredentialStatus.ACTIVE,
            created_at=credential.created_at,
            expires_at=expires_at if expires_at is not None else credential.expires_at,
            revoked_at=None,
            version=credential.version + 1,
        )

        return IssuedDeveloperCredential(
            credential=rotated,
            secret=generated.raw,
        )

    def revoke(
        self,
        credential: DeveloperCredential,
        *,
        when: datetime | None = None,
    ) -> DeveloperCredential:
        return credential.revoke(when=when)
