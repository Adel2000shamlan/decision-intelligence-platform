from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

from fastapi import HTTPException, status

from app.modules.developer.application.service import DeveloperService
from app.modules.developer.domain.models import (
    DeveloperCredential,
    DeveloperCredentialStatus,
)

if TYPE_CHECKING:
    from app.modules.developer.api.router import DeveloperPrincipal


@dataclass(frozen=True, slots=True)
class DeveloperCredentialPrincipal:
    platform: DeveloperPrincipal
    credential: DeveloperCredential
    secret: str


def authenticate_developer_credential(
    *,
    platform: DeveloperPrincipal,
    service: DeveloperService,
    client_id: str | None,
    secret: str | None,
    now: datetime | None = None,
) -> DeveloperCredentialPrincipal:
    """
    Validate a developer credential after platform identity.

    Credential lookup is tenant-scoped so credentials belonging to another
    tenant are not disclosed through the HTTP boundary.
    """

    if not client_id or not client_id.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="developer credential required",
            headers={"WWW-Authenticate": "Developer-Credential"},
        )

    if not secret:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="developer credential required",
            headers={"WWW-Authenticate": "Developer-Credential"},
        )

    credential = service.repository.get_credential_by_client_id(
        platform.tenant_id,
        client_id.strip(),
    )

    if credential is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid developer credential",
            headers={"WWW-Authenticate": "Developer-Credential"},
        )

    if credential.tenant_id != platform.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="developer credential tenant mismatch",
        )

    if credential.status is not DeveloperCredentialStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="developer credential is not active",
            headers={"WWW-Authenticate": "Developer-Credential"},
        )

    try:
        valid = service.credential_security.verify(
            credential,
            secret,
            now=now,
        )
    except (ValueError, TypeError):
        valid = False

    if not valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid developer credential",
            headers={"WWW-Authenticate": "Developer-Credential"},
        )

    return DeveloperCredentialPrincipal(
        platform=platform,
        credential=credential,
        secret=secret,
    )
