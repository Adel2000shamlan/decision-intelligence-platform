from abc import ABC, abstractmethod
from uuid import UUID

from ..domain.models import (
    DeveloperApplication,
    DeveloperCredential,
    MarketplaceListing,
)


class DeveloperRepository(ABC):
    """Persistence contract for tenant-scoped developer API resources."""

    @abstractmethod
    def save_application(
        self,
        application: DeveloperApplication,
    ) -> DeveloperApplication:
        raise NotImplementedError

    @abstractmethod
    def get_application(
        self,
        tenant_id: UUID,
        application_id: UUID,
    ) -> DeveloperApplication | None:
        raise NotImplementedError

    @abstractmethod
    def list_applications(
        self,
        tenant_id: UUID,
    ) -> tuple[DeveloperApplication, ...]:
        raise NotImplementedError

    @abstractmethod
    def delete_application(
        self,
        tenant_id: UUID,
        application_id: UUID,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    def save_credential(
        self,
        credential: DeveloperCredential,
    ) -> DeveloperCredential:
        raise NotImplementedError

    @abstractmethod
    def get_credential(
        self,
        tenant_id: UUID,
        credential_id: UUID,
    ) -> DeveloperCredential | None:
        raise NotImplementedError

    @abstractmethod
    def get_credential_by_client_id(
        self,
        tenant_id: UUID,
        client_id: str,
    ) -> DeveloperCredential | None:
        raise NotImplementedError

    @abstractmethod
    def list_credentials(
        self,
        tenant_id: UUID,
        *,
        application_id: UUID | None = None,
    ) -> tuple[DeveloperCredential, ...]:
        raise NotImplementedError

    @abstractmethod
    def delete_credential(
        self,
        tenant_id: UUID,
        credential_id: UUID,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    def save_listing(
        self,
        listing: MarketplaceListing,
    ) -> MarketplaceListing:
        raise NotImplementedError

    @abstractmethod
    def get_listing(
        self,
        tenant_id: UUID,
        listing_id: UUID,
    ) -> MarketplaceListing | None:
        raise NotImplementedError

    @abstractmethod
    def list_listings(
        self,
        tenant_id: UUID,
    ) -> tuple[MarketplaceListing, ...]:
        raise NotImplementedError

    @abstractmethod
    def delete_listing(
        self,
        tenant_id: UUID,
        listing_id: UUID,
    ) -> None:
        raise NotImplementedError
