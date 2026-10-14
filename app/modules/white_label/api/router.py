from __future__ import annotations

from dataclasses import dataclass

from fastapi import APIRouter, Depends, Header, HTTPException, status

from app.modules.authentication.api import tokens
from app.modules.authentication.security import (
    TokenError,
    TokenRecord,
    TokenType,
)
from app.modules.white_label.api.contract import (
    WhiteLabelResponse,
    WhiteLabelWriteRequest,
)
from app.modules.white_label.domain.models import WhiteLabelConfiguration
from app.shared.domain.errors import (
    BusinessRuleViolation,
    EntityNotFound,
)


router = APIRouter(
    prefix="/white-label",
    tags=["white-label"],
)


@dataclass(frozen=True, slots=True)
class WhiteLabelPrincipal:
    user_id: object
    tenant_id: object
    session_id: object


_service = None


def configure_service(service) -> None:
    global _service
    _service = service


def _get_service():
    if _service is None:
        raise RuntimeError("white-label service is not configured")
    return _service


def require_platform_identity(
    authorization: str | None = Header(default=None),
) -> WhiteLabelPrincipal:
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
            detail="invalid authentication scheme",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        record: TokenRecord = tokens.validate(
            raw.strip(),
            TokenType.ACCESS,
        )
    except TokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid or expired access token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if record.tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="tenant context is required",
        )

    return WhiteLabelPrincipal(
        user_id=record.user_id,
        tenant_id=record.tenant_id,
        session_id=record.session_id,
    )


def _response(
    configuration: WhiteLabelConfiguration,
) -> WhiteLabelResponse:
    return WhiteLabelResponse(
        id=configuration.id,
        tenant_id=configuration.tenant_id,
        organization_id=configuration.organization_id,
        display_name=configuration.display_name,
        short_name=configuration.short_name,
        description=configuration.description,
        logo_url=configuration.logo_url,
        favicon_url=configuration.favicon_url,
        primary_color=configuration.primary_color,
        secondary_color=configuration.secondary_color,
        background_color=configuration.background_color,
        theme_color=configuration.theme_color,
        locale=configuration.locale,
        direction=configuration.direction,
        created_at=configuration.created_at,
        updated_at=configuration.updated_at,
        version=configuration.version,
    )


def _handle_domain_error(exc: Exception) -> None:
    if isinstance(exc, EntityNotFound):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )

    if isinstance(exc, BusinessRuleViolation):
        message = str(exc)

        if "already exists" in message:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=message,
            )

        if "tenant mismatch" in message:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="white-label configuration not found",
            )

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message,
        )

    if isinstance(exc, PermissionError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        )

    raise exc


@router.get(
    "",
    response_model=WhiteLabelResponse,
)
def get_white_label(
    principal: WhiteLabelPrincipal = Depends(require_platform_identity),
):
    try:
        configuration = _get_service().get(
            tenant_id=principal.tenant_id,
            actor_id=principal.user_id,
            authentication_id=principal.session_id,
        )
        return _response(configuration)
    except Exception as exc:
        _handle_domain_error(exc)


@router.post(
    "",
    response_model=WhiteLabelResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_white_label(
    payload: WhiteLabelWriteRequest,
    principal: WhiteLabelPrincipal = Depends(require_platform_identity),
):
    try:
        configuration = _get_service().create(
            tenant_id=principal.tenant_id,
            actor_id=principal.user_id,
            authentication_id=principal.session_id,
            organization_id=payload.organization_id,
            display_name=payload.display_name,
            short_name=payload.short_name,
            description=payload.description,
            logo_url=payload.logo_url,
            favicon_url=payload.favicon_url,
            primary_color=payload.primary_color,
            secondary_color=payload.secondary_color,
            background_color=payload.background_color,
            theme_color=payload.theme_color,
            locale=payload.locale,
            direction=payload.direction,
        )
        return _response(configuration)
    except Exception as exc:
        _handle_domain_error(exc)


@router.put(
    "",
    response_model=WhiteLabelResponse,
)
def update_white_label(
    payload: WhiteLabelWriteRequest,
    principal: WhiteLabelPrincipal = Depends(require_platform_identity),
):
    try:
        existing = _get_service().get(
            tenant_id=principal.tenant_id,
            actor_id=principal.user_id,
            authentication_id=principal.session_id,
        )

        persisted = _get_service().repository.get_by_tenant(
            principal.tenant_id
        )

        if persisted is None:
            raise EntityNotFound(
                "white-label configuration not found"
            )

        configuration = _get_service().update(
            tenant_id=principal.tenant_id,
            configuration_id=existing.id,
            actor_id=principal.user_id,
            authentication_id=principal.session_id,
            organization_id=payload.organization_id,
            display_name=payload.display_name,
            short_name=payload.short_name,
            description=payload.description,
            logo_url=payload.logo_url,
            favicon_url=payload.favicon_url,
            primary_color=payload.primary_color,
            secondary_color=payload.secondary_color,
            background_color=payload.background_color,
            theme_color=payload.theme_color,
            locale=payload.locale,
            direction=payload.direction,
        )
        return _response(configuration)
    except Exception as exc:
        _handle_domain_error(exc)


@router.delete(
    "",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_white_label(
    principal: WhiteLabelPrincipal = Depends(require_platform_identity),
):
    try:
        configuration = _get_service().repository.get_by_tenant(
            principal.tenant_id
        )

        if configuration is None:
            raise EntityNotFound(
                "white-label configuration not found"
            )

        _get_service().delete(
            tenant_id=principal.tenant_id,
            configuration_id=configuration.id,
            actor_id=principal.user_id,
            authentication_id=principal.session_id,
        )
    except Exception as exc:
        _handle_domain_error(exc)
