from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field

from app.modules.authentication.api import tokens
from app.modules.authentication.security import TokenError, TokenType
from app.modules.developer.application.service import DeveloperService
from app.modules.developer.domain.models import (
    APIScope,
    DeveloperApplicationStatus,
    DeveloperCredentialStatus,
)
from app.shared.domain.errors import BusinessRuleViolation


router = APIRouter(prefix="/developer", tags=["developer"])

_service: DeveloperService | None = None


def configure_service(service: DeveloperService) -> None:
    global _service
    _service = service


def _get_service() -> DeveloperService:
    if _service is None:
        raise RuntimeError("developer service is not configured")
    return _service


class DeveloperApplicationCreateRequest(BaseModel):
    tenant_id: UUID
    name: str = Field(min_length=1, max_length=200)


class DeveloperApplicationResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    name: str
    status: DeveloperApplicationStatus
    created_at: datetime
    updated_at: datetime
    version: int


class DeveloperApplicationStatusRequest(BaseModel):
    status: DeveloperApplicationStatus


class DeveloperCredentialCreateRequest(BaseModel):
    client_id: str = Field(min_length=1, max_length=200)
    scopes: tuple[APIScope, ...] = ()
    expires_at: datetime | None = None


class DeveloperCredentialResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    application_id: UUID
    client_id: str
    scopes: tuple[APIScope, ...]
    status: DeveloperCredentialStatus
    created_at: datetime
    expires_at: datetime | None
    revoked_at: datetime | None
    version: int


class IssuedDeveloperCredentialResponse(DeveloperCredentialResponse):
    secret: str


class DeveloperCredentialRotateRequest(BaseModel):
    scopes: tuple[APIScope, ...] | None = None
    expires_at: datetime | None = None


class MarketplaceListingCreateRequest(BaseModel):
    publisher_application_id: UUID
    name: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=2000)
    capability: str = Field(min_length=1, max_length=200)


class MarketplaceListingResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    publisher_application_id: UUID
    name: str
    description: str
    capability: str
    published: bool
    created_at: datetime
    updated_at: datetime
    version: int


class DeveloperPrincipal:
    __slots__ = ("user_id", "tenant_id", "roles", "session_id")

    def __init__(self, record) -> None:
        if record.tenant_id is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="developer API requires a tenant-scoped identity",
            )
        self.user_id = record.user_id
        self.tenant_id = record.tenant_id
        self.roles = record.roles
        self.session_id = record.session_id


def require_platform_identity(
    authorization: str | None = Header(default=None),
) -> DeveloperPrincipal:
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    scheme, _, raw = authorization.partition(" ")
    if scheme.lower() != "bearer" or not raw.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid bearer authentication",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        record = tokens.validate(raw.strip(), TokenType.ACCESS)
    except TokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid or expired access token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return DeveloperPrincipal(record)


def _application_response(application) -> DeveloperApplicationResponse:
    return DeveloperApplicationResponse(
        id=application.id,
        tenant_id=application.tenant_id,
        name=application.name,
        status=application.status,
        created_at=application.created_at,
        updated_at=application.updated_at,
        version=application.version,
    )


def _credential_response(credential) -> DeveloperCredentialResponse:
    return DeveloperCredentialResponse(
        id=credential.id,
        tenant_id=credential.tenant_id,
        application_id=credential.application_id,
        client_id=credential.client_id,
        scopes=credential.scopes,
        status=credential.status,
        created_at=credential.created_at,
        expires_at=credential.expires_at,
        revoked_at=credential.revoked_at,
        version=credential.version,
    )


def _issued_response(issued) -> IssuedDeveloperCredentialResponse:
    base = _credential_response(issued.credential)
    return IssuedDeveloperCredentialResponse(
        **base.model_dump(),
        secret=issued.secret,
    )


def _listing_response(listing) -> MarketplaceListingResponse:
    return MarketplaceListingResponse(
        id=listing.id,
        tenant_id=listing.tenant_id,
        publisher_application_id=listing.publisher_application_id,
        name=listing.name,
        description=listing.description,
        capability=listing.capability,
        published=listing.published,
        created_at=listing.created_at,
        updated_at=listing.updated_at,
        version=listing.version,
    )


@router.post(
    "/applications",
    response_model=DeveloperApplicationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_application(
    body: DeveloperApplicationCreateRequest,
    principal: DeveloperPrincipal = Depends(require_platform_identity),
) -> DeveloperApplicationResponse:
    if body.tenant_id != principal.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="tenant mismatch",
        )

    try:
        application = _get_service().create_application(
            tenant_id=principal.tenant_id,
            name=body.name,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return _application_response(application)


@router.get(
    "/applications",
    response_model=tuple[DeveloperApplicationResponse, ...],
)
def list_applications(
    principal: DeveloperPrincipal = Depends(require_platform_identity),
) -> tuple[DeveloperApplicationResponse, ...]:
    applications = _get_service().list_applications(principal.tenant_id)
    return tuple(_application_response(item) for item in applications)


@router.get(
    "/applications/{application_id}",
    response_model=DeveloperApplicationResponse,
)
def get_application(
    application_id: UUID,
    principal: DeveloperPrincipal = Depends(require_platform_identity),
) -> DeveloperApplicationResponse:
    application = _get_service().get_application(
        tenant_id=principal.tenant_id,
        application_id=application_id,
    )
    if application is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="developer application not found")
    return _application_response(application)


@router.patch(
    "/applications/{application_id}/status",
    response_model=DeveloperApplicationResponse,
)
def set_application_status(
    application_id: UUID,
    body: DeveloperApplicationStatusRequest,
    principal: DeveloperPrincipal = Depends(require_platform_identity),
) -> DeveloperApplicationResponse:
    try:
        application = _get_service().set_application_status(
            tenant_id=principal.tenant_id,
            application_id=application_id,
            status=body.status,
        )
    except BusinessRuleViolation as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    return _application_response(application)


@router.post(
    "/applications/{application_id}/credentials",
    response_model=IssuedDeveloperCredentialResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_credential(
    application_id: UUID,
    body: DeveloperCredentialCreateRequest,
    principal: DeveloperPrincipal = Depends(require_platform_identity),
) -> IssuedDeveloperCredentialResponse:
    try:
        issued = _get_service().issue_credential(
            tenant_id=principal.tenant_id,
            application_id=application_id,
            client_id=body.client_id,
            scopes=body.scopes,
            expires_at=body.expires_at,
        )
    except BusinessRuleViolation as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return _issued_response(issued)


@router.get(
    "/applications/{application_id}/credentials",
    response_model=tuple[DeveloperCredentialResponse, ...],
)
def list_application_credentials(
    application_id: UUID,
    principal: DeveloperPrincipal = Depends(require_platform_identity),
) -> tuple[DeveloperCredentialResponse, ...]:
    application = _get_service().get_application(
        tenant_id=principal.tenant_id,
        application_id=application_id,
    )
    if application is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="developer application not found",
        )

    credentials = _get_service().list_credentials(
        principal.tenant_id,
        application_id=application_id,
    )
    return tuple(_credential_response(item) for item in credentials)


@router.get(
    "/credentials/{credential_id}",
    response_model=DeveloperCredentialResponse,
)
def get_credential(
    credential_id: UUID,
    principal: DeveloperPrincipal = Depends(require_platform_identity),
) -> DeveloperCredentialResponse:
    credential = _get_service().get_credential(
        tenant_id=principal.tenant_id,
        credential_id=credential_id,
    )
    if credential is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="developer credential not found",
        )

    return _credential_response(credential)


@router.post(
    "/credentials/{credential_id}/rotate",
    response_model=IssuedDeveloperCredentialResponse,
)
def rotate_credential(
    credential_id: UUID,
    body: DeveloperCredentialRotateRequest,
    principal: DeveloperPrincipal = Depends(require_platform_identity),
) -> IssuedDeveloperCredentialResponse:
    try:
        issued = _get_service().rotate_credential(
            tenant_id=principal.tenant_id,
            credential_id=credential_id,
            scopes=body.scopes,
            expires_at=body.expires_at,
        )
    except BusinessRuleViolation as exc:
        message = str(exc)
        code = (
            status.HTTP_409_CONFLICT
            if "only active credentials" in message
            else status.HTTP_404_NOT_FOUND
        )
        raise HTTPException(
            status_code=code,
            detail=message,
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return _issued_response(issued)


@router.post(
    "/credentials/{credential_id}/revoke",
    response_model=DeveloperCredentialResponse,
)
def revoke_credential(
    credential_id: UUID,
    principal: DeveloperPrincipal = Depends(require_platform_identity),
) -> DeveloperCredentialResponse:
    try:
        credential = _get_service().revoke_credential(
            tenant_id=principal.tenant_id,
            credential_id=credential_id,
        )
    except BusinessRuleViolation as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    return _credential_response(credential)


@router.post(
    "/marketplace/listings",
    response_model=MarketplaceListingResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_marketplace_listing(
    body: MarketplaceListingCreateRequest,
    principal: DeveloperPrincipal = Depends(require_platform_identity),
) -> MarketplaceListingResponse:
    try:
        listing = _get_service().create_listing(
            tenant_id=principal.tenant_id,
            publisher_application_id=body.publisher_application_id,
            name=body.name,
            description=body.description,
            capability=body.capability,
        )
    except BusinessRuleViolation as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return _listing_response(listing)


@router.get(
    "/marketplace/listings",
    response_model=tuple[MarketplaceListingResponse, ...],
)
def list_marketplace_listings(
    principal: DeveloperPrincipal = Depends(require_platform_identity),
) -> tuple[MarketplaceListingResponse, ...]:
    listings = _get_service().list_listings(principal.tenant_id)
    return tuple(_listing_response(item) for item in listings)


@router.get(
    "/marketplace/listings/{listing_id}",
    response_model=MarketplaceListingResponse,
)
def get_marketplace_listing(
    listing_id: UUID,
    principal: DeveloperPrincipal = Depends(require_platform_identity),
) -> MarketplaceListingResponse:
    listing = _get_service().get_listing(
        tenant_id=principal.tenant_id,
        listing_id=listing_id,
    )
    if listing is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="marketplace listing not found",
        )

    return _listing_response(listing)


@router.post(
    "/marketplace/listings/{listing_id}/publish",
    response_model=MarketplaceListingResponse,
)
def publish_marketplace_listing(
    listing_id: UUID,
    principal: DeveloperPrincipal = Depends(require_platform_identity),
) -> MarketplaceListingResponse:
    try:
        listing = _get_service().publish_listing(
            tenant_id=principal.tenant_id,
            listing_id=listing_id,
        )
    except BusinessRuleViolation as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    return _listing_response(listing)


@router.post(
    "/marketplace/listings/{listing_id}/unpublish",
    response_model=MarketplaceListingResponse,
)
def unpublish_marketplace_listing(
    listing_id: UUID,
    principal: DeveloperPrincipal = Depends(require_platform_identity),
) -> MarketplaceListingResponse:
    try:
        listing = _get_service().unpublish_listing(
            tenant_id=principal.tenant_id,
            listing_id=listing_id,
        )
    except BusinessRuleViolation as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    return _listing_response(listing)
