from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass
from typing import Protocol
from uuid import UUID

from app.shared.domain.errors import BusinessRuleViolation, InvalidDomainData


class CredentialBoundaryViolation(BusinessRuleViolation):
    """Raised when credential material crosses the User domain boundary."""


FORBIDDEN_CREDENTIAL_NAMES = frozenset({
    "password", "password_hash", "password_digest", "salt", "secret",
    "refresh_token", "access_token", "token", "token_hash", "api_key",
    "private_key", "otp", "otp_secret", "credential", "credentials",
})


@dataclass(frozen=True)
class SecurityActorContext:
    """Minimal security metadata allowed to cross into domain operations."""
    actor_id: UUID | None = None
    correlation_id: UUID | None = None


class CredentialStorePort(Protocol):
    """Future application/infrastructure contract; never implemented by User."""
    def has_credentials(self, user_id: UUID) -> bool: ...
    def revoke_credentials(self, user_id: UUID, *, actor_id: UUID | None = None) -> None: ...


class CredentialBoundaryContract:
    """Enforces separation between identity/lifecycle and credential material."""

    @staticmethod
    def assert_user_boundary(user: object) -> None:
        declared = {f.name.lower() for f in fields(user)} if is_dataclass(user) else set()
        leaked_declared = declared & FORBIDDEN_CREDENTIAL_NAMES
        if leaked_declared:
            raise CredentialBoundaryViolation(
                f"credential material is forbidden in User aggregate: {sorted(leaked_declared)[0]}"
            )
        runtime = {name.lower() for name in getattr(user, "__dict__", {})} | {name.lower() for name in dir(type(user)) if not name.startswith("__")}
        leaked_runtime = runtime & FORBIDDEN_CREDENTIAL_NAMES
        if leaked_runtime:
            raise CredentialBoundaryViolation(
                f"credential material is forbidden in User aggregate: {sorted(leaked_runtime)[0]}"
            )

    @staticmethod
    def assert_event_safe(event: object) -> None:
        names = {f.name.lower() for f in fields(event)} if is_dataclass(event) else set()
        runtime = {name.lower() for name in getattr(event, "__dict__", {})} | {name.lower() for name in dir(type(event)) if not name.startswith("__")}
        leaked = (names | runtime) & FORBIDDEN_CREDENTIAL_NAMES
        if leaked:
            raise CredentialBoundaryViolation(
                f"credential material is forbidden in User events: {sorted(leaked)[0]}"
            )
