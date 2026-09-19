from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from uuid import UUID, uuid4

from app.shared.domain.aggregate import AggregateRoot
from app.shared.domain.errors import InvalidDomainData


class DeveloperApplicationStatus(str, Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    ARCHIVED = "archived"


class DeveloperCredentialStatus(str, Enum):
    ACTIVE = "active"
    REVOKED = "revoked"
    EXPIRED = "expired"


class APIScope(str, Enum):
    PROJECTS_READ = "projects:read"
    PROJECTS_WRITE = "projects:write"
    DECISIONS_READ = "decisions:read"
    DECISIONS_WRITE = "decisions:write"
    RISKS_READ = "risks:read"
    RISKS_WRITE = "risks:write"


@dataclass
class DeveloperApplication(AggregateRoot):
    tenant_id: UUID
    name: str
    id: UUID = field(default_factory=uuid4)
    status: DeveloperApplicationStatus = DeveloperApplicationStatus.ACTIVE
    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    updated_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    version: int = 1

    def __post_init__(self) -> None:
        if not isinstance(self.tenant_id, UUID):
            raise InvalidDomainData("tenant_id must be UUID")

        if not isinstance(self.name, str):
            raise InvalidDomainData("name must be a string")

        self.name = self.name.strip()

        if not self.name:
            raise InvalidDomainData("name is required")

        if len(self.name) > 200:
            raise InvalidDomainData("name exceeds 200 characters")

        if not isinstance(self.status, DeveloperApplicationStatus):
            try:
                self.status = DeveloperApplicationStatus(self.status)
            except (TypeError, ValueError) as exc:
                raise InvalidDomainData(
                    "invalid developer application status"
                ) from exc

        if not isinstance(self.id, UUID):
            raise InvalidDomainData("id must be UUID")

        if self.version < 1:
            raise InvalidDomainData("version must be >= 1")

    def validate_invariants(self) -> None:
        super().validate_invariants()

        if self.updated_at < self.created_at:
            raise InvalidDomainData(
                "updated_at cannot precede created_at"
            )

    @classmethod
    def create(
        cls,
        tenant_id: UUID,
        name: str,
    ) -> "DeveloperApplication":
        return cls(
            tenant_id=tenant_id,
            name=name,
        )


@dataclass(frozen=True)
class DeveloperCredential:
    id: UUID
    tenant_id: UUID
    application_id: UUID
    client_id: str
    secret_hash: str
    scopes: tuple[APIScope, ...]
    status: DeveloperCredentialStatus
    created_at: datetime
    expires_at: datetime | None = None
    revoked_at: datetime | None = None
    version: int = 1

    @classmethod
    def create(
        cls,
        *,
        tenant_id: UUID,
        application_id: UUID,
        client_id: str,
        secret_hash: str,
        scopes: tuple[APIScope, ...] | list[APIScope] = (),
        expires_at: datetime | None = None,
    ) -> "DeveloperCredential":
        if not isinstance(tenant_id, UUID):
            raise InvalidDomainData("tenant_id must be UUID")

        if not isinstance(application_id, UUID):
            raise InvalidDomainData("application_id must be UUID")

        if not isinstance(client_id, str) or not client_id.strip():
            raise InvalidDomainData("client_id is required")

        if not isinstance(secret_hash, str) or not secret_hash.strip():
            raise InvalidDomainData("secret_hash is required")

        if secret_hash.strip() == client_id.strip():
            raise InvalidDomainData(
                "secret_hash must not equal client_id"
            )

        normalized_scopes: list[APIScope] = []

        for scope in scopes:
            try:
                normalized = APIScope(scope)
            except (TypeError, ValueError) as exc:
                raise InvalidDomainData(
                    "invalid API scope"
                ) from exc

            if normalized not in normalized_scopes:
                normalized_scopes.append(normalized)

        created_at = datetime.now(timezone.utc)

        if expires_at is not None:
            if (
                not isinstance(expires_at, datetime)
                or expires_at.tzinfo is None
            ):
                raise InvalidDomainData(
                    "expires_at must be timezone-aware datetime"
                )

            if expires_at <= created_at:
                raise InvalidDomainData(
                    "expires_at must be after created_at"
                )

        return cls(
            id=uuid4(),
            tenant_id=tenant_id,
            application_id=application_id,
            client_id=client_id.strip(),
            secret_hash=secret_hash.strip(),
            scopes=tuple(normalized_scopes),
            status=DeveloperCredentialStatus.ACTIVE,
            created_at=created_at,
            expires_at=expires_at,
            version=1,
        )

    def is_expired(self, now: datetime | None = None) -> bool:
        if self.expires_at is None:
            return False

        current = now or datetime.now(timezone.utc)

        if current.tzinfo is None:
            raise InvalidDomainData("now must be timezone-aware datetime")

        return current >= self.expires_at

    def has_scope(self, scope: APIScope | str) -> bool:
        try:
            scope = APIScope(scope)
        except (TypeError, ValueError):
            return False

        return scope in self.scopes

    def revoke(self, when: datetime | None = None) -> "DeveloperCredential":
        revoked_at = when or datetime.now(timezone.utc)

        if revoked_at.tzinfo is None:
            raise InvalidDomainData(
                "revoked_at must be timezone-aware datetime"
            )

        return DeveloperCredential(
            id=self.id,
            tenant_id=self.tenant_id,
            application_id=self.application_id,
            client_id=self.client_id,
            secret_hash=self.secret_hash,
            scopes=self.scopes,
            status=DeveloperCredentialStatus.REVOKED,
            created_at=self.created_at,
            expires_at=self.expires_at,
            revoked_at=revoked_at,
            version=self.version + 1,
        )


@dataclass(frozen=True)
class MarketplaceListing:
    id: UUID
    tenant_id: UUID
    publisher_application_id: UUID
    name: str
    description: str
    capability: str
    published: bool
    created_at: datetime
    updated_at: datetime
    version: int = 1

    @classmethod
    def create(
        cls,
        *,
        tenant_id: UUID,
        publisher_application_id: UUID,
        name: str,
        description: str,
        capability: str,
    ) -> "MarketplaceListing":
        if not isinstance(tenant_id, UUID):
            raise InvalidDomainData("tenant_id must be UUID")

        if not isinstance(publisher_application_id, UUID):
            raise InvalidDomainData(
                "publisher_application_id must be UUID"
            )

        values = {
            "name": name,
            "description": description,
            "capability": capability,
        }

        for field_name, value in values.items():
            if not isinstance(value, str) or not value.strip():
                raise InvalidDomainData(
                    f"{field_name} is required"
                )

        now = datetime.now(timezone.utc)

        return cls(
            id=uuid4(),
            tenant_id=tenant_id,
            publisher_application_id=publisher_application_id,
            name=name.strip(),
            description=description.strip(),
            capability=capability.strip(),
            published=False,
            created_at=now,
            updated_at=now,
            version=1,
        )

    def publish(self) -> "MarketplaceListing":
        now = datetime.now(timezone.utc)

        return MarketplaceListing(
            id=self.id,
            tenant_id=self.tenant_id,
            publisher_application_id=self.publisher_application_id,
            name=self.name,
            description=self.description,
            capability=self.capability,
            published=True,
            created_at=self.created_at,
            updated_at=now,
            version=self.version + 1,
        )

    def unpublish(self) -> "MarketplaceListing":
        now = datetime.now(timezone.utc)

        return MarketplaceListing(
            id=self.id,
            tenant_id=self.tenant_id,
            publisher_application_id=self.publisher_application_id,
            name=self.name,
            description=self.description,
            capability=self.capability,
            published=False,
            created_at=self.created_at,
            updated_at=now,
            version=self.version + 1,
        )
