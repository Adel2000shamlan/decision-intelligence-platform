from datetime import datetime
from uuid import UUID

from ..domain.models import (
    APIScope,
    DeveloperApplication,
    DeveloperApplicationStatus,
    DeveloperCredential,
    DeveloperCredentialStatus,
    MarketplaceListing,
)


def application_to_row(application: DeveloperApplication) -> tuple:
    return (
        str(application.id),
        str(application.tenant_id),
        application.name,
        application.status.value,
        application.created_at.isoformat(),
        application.updated_at.isoformat(),
        application.version,
    )


def application_from_row(row) -> DeveloperApplication:
    return DeveloperApplication(
        id=UUID(str(row["id"])),
        tenant_id=UUID(str(row["tenant_id"])),
        name=row["name"],
        status=DeveloperApplicationStatus(row["status"]),
        created_at=(
            row["created_at"]
            if isinstance(row["created_at"], datetime)
            else datetime.fromisoformat(str(row["created_at"]))
        ),
        updated_at=(
            row["updated_at"]
            if isinstance(row["updated_at"], datetime)
            else datetime.fromisoformat(str(row["updated_at"]))
        ),
        version=int(row["version"]),
    )


def credential_to_row(credential: DeveloperCredential) -> tuple:
    return (
        str(credential.id),
        str(credential.tenant_id),
        str(credential.application_id),
        credential.client_id,
        credential.secret_hash,
        ",".join(scope.value for scope in credential.scopes),
        credential.status.value,
        credential.created_at.isoformat(),
        credential.expires_at.isoformat() if credential.expires_at else None,
        credential.revoked_at.isoformat() if credential.revoked_at else None,
        credential.version,
    )


def credential_from_row(row) -> DeveloperCredential:
    raw_scopes = row["scopes"] or ""
    scopes = tuple(
        APIScope(scope)
        for scope in raw_scopes.split(",")
        if scope
    )

    return DeveloperCredential(
        id=UUID(str(row["id"])),
        tenant_id=UUID(str(row["tenant_id"])),
        application_id=UUID(str(row["application_id"])),
        client_id=row["client_id"],
        secret_hash=row["secret_hash"],
        scopes=scopes,
        status=DeveloperCredentialStatus(row["status"]),
        created_at=(
            row["created_at"]
            if isinstance(row["created_at"], datetime)
            else datetime.fromisoformat(str(row["created_at"]))
        ),
        expires_at=(
            row["expires_at"]
            if isinstance(row["expires_at"], datetime)
            else datetime.fromisoformat(str(row["expires_at"]))
        )
        if row["expires_at"]
        else None,
        revoked_at=(
            row["revoked_at"]
            if isinstance(row["revoked_at"], datetime)
            else datetime.fromisoformat(str(row["revoked_at"]))
        )
        if row["revoked_at"]
        else None,
        version=int(row["version"]),
    )


def listing_to_row(listing: MarketplaceListing) -> tuple:
    return (
        str(listing.id),
        str(listing.tenant_id),
        str(listing.publisher_application_id),
        listing.name,
        listing.description,
        listing.capability,
        listing.published,
        listing.created_at.isoformat(),
        listing.updated_at.isoformat(),
        listing.version,
    )


def listing_from_row(row) -> MarketplaceListing:
    return MarketplaceListing(
        id=UUID(str(row["id"])),
        tenant_id=UUID(str(row["tenant_id"])),
        publisher_application_id=UUID(str(row["publisher_application_id"])),
        name=row["name"],
        description=row["description"],
        capability=row["capability"],
        published=bool(row["published"]),
        created_at=(
            row["created_at"]
            if isinstance(row["created_at"], datetime)
            else datetime.fromisoformat(str(row["created_at"]))
        ),
        updated_at=(
            row["updated_at"]
            if isinstance(row["updated_at"], datetime)
            else datetime.fromisoformat(str(row["updated_at"]))
        ),
        version=int(row["version"]),
    )
