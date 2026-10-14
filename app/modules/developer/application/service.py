from __future__ import annotations

from datetime import datetime
from uuid import UUID

from app.shared.domain.errors import BusinessRuleViolation

from ..domain.models import (
    APIScope,
    DeveloperApplication,
    DeveloperApplicationStatus,
    DeveloperCredential,
    DeveloperCredentialStatus,
    MarketplaceListing,
)
from ..persistence.repository import DeveloperRepository
from ..security.credentials import (
    DeveloperCredentialSecurityService,
    IssuedDeveloperCredential,
)


class DeveloperService:
    """Application boundary for Developer API and Marketplace resources."""

    def __init__(
        self,
        repository: DeveloperRepository,
        credential_security: DeveloperCredentialSecurityService | None = None,
    ) -> None:
        self.repository = repository
        self.credential_security = (
            credential_security or DeveloperCredentialSecurityService()
        )

    # ------------------------------------------------------------------
    # Applications
    # ------------------------------------------------------------------

    def create_application(
        self,
        *,
        tenant_id: UUID,
        name: str,
    ) -> DeveloperApplication:
        application = DeveloperApplication.create(
            tenant_id=tenant_id,
            name=name,
        )
        return self.repository.save_application(application)

    def get_application(
        self,
        *,
        tenant_id: UUID,
        application_id: UUID,
    ) -> DeveloperApplication | None:
        return self.repository.get_application(
            tenant_id,
            application_id,
        )

    def list_applications(
        self,
        tenant_id: UUID,
    ) -> tuple[DeveloperApplication, ...]:
        return self.repository.list_applications(tenant_id)

    def set_application_status(
        self,
        *,
        tenant_id: UUID,
        application_id: UUID,
        status: DeveloperApplicationStatus,
    ) -> DeveloperApplication:
        application = self.repository.get_application(
            tenant_id,
            application_id,
        )
        if application is None:
            raise BusinessRuleViolation("application not found")

        try:
            normalized_status = DeveloperApplicationStatus(status)
        except (TypeError, ValueError) as exc:
            raise BusinessRuleViolation("invalid application status") from exc

        updated = DeveloperApplication(
            id=application.id,
            tenant_id=application.tenant_id,
            name=application.name,
            status=normalized_status,
            created_at=application.created_at,
            updated_at=datetime.now(application.updated_at.tzinfo),
            version=application.version + 1,
        )

        return self.repository.save_application(updated)

    # ------------------------------------------------------------------
    # Credentials
    # ------------------------------------------------------------------

    def _active_application(
        self,
        *,
        tenant_id: UUID,
        application_id: UUID,
    ) -> DeveloperApplication:
        application = self.repository.get_application(
            tenant_id,
            application_id,
        )
        if application is None:
            raise BusinessRuleViolation("application not found")

        if application.status is not DeveloperApplicationStatus.ACTIVE:
            raise BusinessRuleViolation("application is not active")

        return application

    def issue_credential(
        self,
        *,
        tenant_id: UUID,
        application_id: UUID,
        client_id: str,
        scopes: tuple[APIScope, ...] = (),
        expires_at: datetime | None = None,
    ) -> IssuedDeveloperCredential:
        self._active_application(
            tenant_id=tenant_id,
            application_id=application_id,
        )

        issued = self.credential_security.issue(
            tenant_id=tenant_id,
            application_id=application_id,
            client_id=client_id,
            scopes=scopes,
            expires_at=expires_at,
        )


        self.repository.save_credential(issued.credential)
        return issued

    def get_credential(
        self,
        *,
        tenant_id: UUID,
        credential_id: UUID,
    ) -> DeveloperCredential | None:
        return self.repository.get_credential(
            tenant_id,
            credential_id,
        )

    def list_credentials(
        self,
        tenant_id: UUID,
        *,
        application_id: UUID | None = None,
    ) -> tuple[DeveloperCredential, ...]:
        return self.repository.list_credentials(
            tenant_id,
            application_id=application_id,
        )

    def verify_credential(
        self,
        *,
        tenant_id: UUID,
        credential_id: UUID,
        secret: str,
    ) -> bool:
        credential = self.repository.get_credential(
            tenant_id,
            credential_id,
        )
        if credential is None:
            return False

        return self.credential_security.verify(
            credential,
            secret,
        )

    def revoke_credential(
        self,
        *,
        tenant_id: UUID,
        credential_id: UUID,
    ) -> DeveloperCredential:
        credential = self.repository.get_credential(
            tenant_id,
            credential_id,
        )
        if credential is None:
            raise BusinessRuleViolation("credential not found")

        revoked = self.credential_security.revoke(credential)
        return self.repository.save_credential(revoked)

    def rotate_credential(
        self,
        *,
        tenant_id: UUID,
        credential_id: UUID,
        scopes: tuple[APIScope, ...] | None = None,
        expires_at: datetime | None = None,
    ) -> IssuedDeveloperCredential:
        credential = self.repository.get_credential(
            tenant_id,
            credential_id,
        )
        if credential is None:
            raise BusinessRuleViolation("credential not found")

        if credential.status is not DeveloperCredentialStatus.ACTIVE:
            raise BusinessRuleViolation(
                "only active credentials can be rotated"
            )

        application = self.repository.get_application(
            tenant_id,
            credential.application_id,
        )
        if application is None:
            raise BusinessRuleViolation("application not found")

        if application.status is not DeveloperApplicationStatus.ACTIVE:
            raise BusinessRuleViolation("application is not active")

        rotated = self.credential_security.rotate(
            credential,
            scopes=scopes,
            expires_at=expires_at,
        )

        saved = self.repository.save_credential(rotated.credential)

        return IssuedDeveloperCredential(
            credential=saved,
            secret=rotated.secret,
        )

    # ------------------------------------------------------------------
    # Marketplace
    # ------------------------------------------------------------------

    def create_listing(
        self,
        *,
        tenant_id: UUID,
        publisher_application_id: UUID,
        name: str,
        description: str,
        capability: str,
    ) -> MarketplaceListing:
        self._active_application(
            tenant_id=tenant_id,
            application_id=publisher_application_id,
        )

        listing = MarketplaceListing.create(
            tenant_id=tenant_id,
            publisher_application_id=publisher_application_id,
            name=name,
            description=description,
            capability=capability,
        )

        return self.repository.save_listing(listing)

    def get_listing(
        self,
        *,
        tenant_id: UUID,
        listing_id: UUID,
    ) -> MarketplaceListing | None:
        return self.repository.get_listing(
            tenant_id,
            listing_id,
        )

    def list_listings(
        self,
        tenant_id: UUID,
    ) -> tuple[MarketplaceListing, ...]:
        return self.repository.list_listings(tenant_id)

    def publish_listing(
        self,
        *,
        tenant_id: UUID,
        listing_id: UUID,
    ) -> MarketplaceListing:
        listing = self.repository.get_listing(
            tenant_id,
            listing_id,
        )
        if listing is None:
            raise BusinessRuleViolation("listing not found")

        application = self.repository.get_application(
            tenant_id,
            listing.publisher_application_id,
        )
        if application is None:
            raise BusinessRuleViolation("application not found")

        if application.status is not DeveloperApplicationStatus.ACTIVE:
            raise BusinessRuleViolation("application is not active")

        return self.repository.save_listing(listing.publish())

    def unpublish_listing(
        self,
        *,
        tenant_id: UUID,
        listing_id: UUID,
    ) -> MarketplaceListing:
        listing = self.repository.get_listing(
            tenant_id,
            listing_id,
        )
        if listing is None:
            raise BusinessRuleViolation("listing not found")

        return self.repository.save_listing(listing.unpublish())

    def remove_application(
        self,
        *,
        tenant_id: UUID,
        application_id: UUID,
    ) -> None:
        application = self.repository.get_application(
            tenant_id,
            application_id,
        )
        if application is None:
            raise BusinessRuleViolation("application not found")

        self.repository.delete_application(
            tenant_id,
            application_id,
        )

    def remove_credential(
        self,
        *,
        tenant_id: UUID,
        credential_id: UUID,
    ) -> None:
        credential = self.repository.get_credential(
            tenant_id,
            credential_id,
        )
        if credential is None:
            raise BusinessRuleViolation("credential not found")

        self.repository.delete_credential(
            tenant_id,
            credential_id,
        )

    def remove_listing(
        self,
        *,
        tenant_id: UUID,
        listing_id: UUID,
    ) -> None:
        listing = self.repository.get_listing(
            tenant_id,
            listing_id,
        )
        if listing is None:
            raise BusinessRuleViolation("listing not found")

        self.repository.delete_listing(
            tenant_id,
            listing_id,
        )
