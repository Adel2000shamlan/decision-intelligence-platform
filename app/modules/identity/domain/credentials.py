from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from uuid import UUID
from app.shared.domain.errors import InvalidDomainData, BusinessRuleViolation

class CredentialStatus(str, Enum): ACTIVE="active"; REVOKED="revoked"; EXPIRED="expired"

@dataclass(frozen=True, slots=True)
class CredentialReference:
    credential_id: UUID
    user_id: UUID
    kind: str
    status: CredentialStatus = CredentialStatus.ACTIVE
    created_at: datetime = datetime.now(timezone.utc)
    expires_at: datetime | None = None
    def __post_init__(self):
        if not isinstance(self.credential_id, UUID) or not isinstance(self.user_id, UUID): raise InvalidDomainData("credential ids must be UUID")
        if not self.kind.strip(): raise InvalidDomainData("credential kind is required")
        if self.expires_at and self.expires_at < self.created_at: raise InvalidDomainData("credential expiry precedes creation")

class CredentialOwnershipContract:
    @staticmethod
    def assert_user_can_authenticate(user, credential_exists: bool) -> None:
        if not credential_exists: raise BusinessRuleViolation("credential does not exist")
        if not user.is_active: raise BusinessRuleViolation("user is not eligible for authentication")
    @staticmethod
    def assert_reference_safe(reference: CredentialReference) -> None:
        if not isinstance(reference, CredentialReference): raise InvalidDomainData("invalid credential reference")
        if reference.status is CredentialStatus.REVOKED: raise BusinessRuleViolation("credential is revoked")
