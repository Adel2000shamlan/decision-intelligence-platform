from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, status

from app.modules.authorization.domain.models import (
    Action,
    Resource,
    ResourceType,
)
from app.modules.developer.api.router import (
    DeveloperPrincipal,
    _get_service,
    require_platform_identity,
)
from app.modules.developer.authorization.adapter import (
    DeveloperAuthorizationError,
    DeveloperAuthorizationService,
)
from app.modules.developer.authorization.http import (
    authenticate_developer_credential,
)
from app.modules.developer.authorization.resource_resolver import (
    DeveloperResourceResolver,
)
from app.modules.developer.usage.rate_control import DeveloperRateController


router = APIRouter(prefix="/developer/resources", tags=["developer-resources"])

_resource_authorization: DeveloperAuthorizationService | None = None
_resource_rate_controller: DeveloperRateController | None = None


def configure_resource_authorization(
    authorization: DeveloperAuthorizationService,
) -> None:
    global _resource_authorization
    _resource_authorization = authorization


def _get_authorization() -> DeveloperAuthorizationService:
    if _resource_authorization is None:
        raise RuntimeError("developer resource authorization is not configured")
    return _resource_authorization


def configure_resource_rate_controller(
    controller: DeveloperRateController,
) -> None:
    global _resource_rate_controller
    _resource_rate_controller = controller


def _get_rate_controller() -> DeveloperRateController:
    if _resource_rate_controller is None:
        raise RuntimeError("developer resource rate controller is not configured")
    return _resource_rate_controller


def _authenticate(
    *,
    principal: DeveloperPrincipal,
    client_id: str | None,
    secret: str | None,
):
    return authenticate_developer_credential(
        platform=principal,
        service=_get_service(),
        client_id=client_id,
        secret=secret,
    )


def _authorize_read(
    *,
    principal: DeveloperPrincipal,
    client_id: str | None,
    secret: str | None,
    resource_type: ResourceType,
    resource_id: UUID,
):
    authenticated = _authenticate(
        principal=principal,
        client_id=client_id,
        secret=secret,
    )

    if not _get_rate_controller().allow(
        tenant_id=principal.tenant_id,
        application_id=authenticated.credential.application_id,
    ):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="developer rate limit exceeded",
        )

    resource = Resource(
        resource_type=resource_type,
        resource_id=resource_id,
        tenant_id=principal.tenant_id,
    )

    try:
        return _get_authorization().require(
            credential=authenticated.credential,
            secret=authenticated.secret,
            user_id=principal.user_id,
            authentication_id=principal.session_id,
            tenant_id=principal.tenant_id,
            resource=resource,
            action=Action.READ,
        )
    except DeveloperAuthorizationError as exc:
        message = str(exc)

        if message == "protected resource was not found":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="resource not found",
            ) from exc

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=message,
        ) from exc


def _project_response(project):
    return {
        "id": str(project.id),
        "organization_id": str(project.organization_id),
        "name": project.name,
        "status": project.status.value,
        "version": project.version,
    }


def _decision_response(decision):
    return {
        "id": str(decision.id),
        "organization_id": str(decision.organization_id),
        "project_id": str(decision.project_id),
        "title": decision.title,
        "description": decision.description,
        "decision_type": decision.decision_type.value,
        "priority": decision.priority.value,
        "status": decision.status.value,
        "version": decision.version,
        "created_at": decision.created_at.isoformat(),
        "updated_at": decision.updated_at.isoformat(),
    }


def _risk_response(risk):
    return {
        "id": str(risk.id),
        "project_id": str(risk.project_id),
        "decision_id": (
            str(risk.decision_id)
            if risk.decision_id is not None
            else None
        ),
        "title": risk.title,
        "description": risk.description,
        "status": risk.status.value,
        "source": risk.source.value,
        "version": risk.version,
        "created_at": risk.created_at.isoformat(),
        "updated_at": risk.updated_at.isoformat(),
    }


@router.get("/projects/{project_id}")
def get_project(
    project_id: UUID,
    principal: DeveloperPrincipal = Depends(require_platform_identity),
    client_id: str | None = Header(default=None, alias="X-Developer-Client-ID"),
    secret: str | None = Header(default=None, alias="X-Developer-Secret"),
):
    _authorize_read(
        principal=principal,
        client_id=client_id,
        secret=secret,
        resource_type=ResourceType.PROJECT,
        resource_id=project_id,
    )

    resolver = _get_authorization().resource_resolver
    if not isinstance(resolver, DeveloperResourceResolver):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="developer resource resolver is not configured",
        )

    project = resolver.project_repository.get_by_id(project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="project not found",
        )

    return _project_response(project)


@router.get("/decisions/{decision_id}")
def get_decision(
    decision_id: UUID,
    principal: DeveloperPrincipal = Depends(require_platform_identity),
    client_id: str | None = Header(default=None, alias="X-Developer-Client-ID"),
    secret: str | None = Header(default=None, alias="X-Developer-Secret"),
):
    _authorize_read(
        principal=principal,
        client_id=client_id,
        secret=secret,
        resource_type=ResourceType.DECISION,
        resource_id=decision_id,
    )

    resolver = _get_authorization().resource_resolver
    if not isinstance(resolver, DeveloperResourceResolver):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="developer resource resolver is not configured",
        )

    decision = resolver.decision_repository.get_by_id(decision_id)
    if decision is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="decision not found",
        )

    return _decision_response(decision)


@router.get("/risks/{risk_id}")
def get_risk(
    risk_id: UUID,
    principal: DeveloperPrincipal = Depends(require_platform_identity),
    client_id: str | None = Header(default=None, alias="X-Developer-Client-ID"),
    secret: str | None = Header(default=None, alias="X-Developer-Secret"),
):
    _authorize_read(
        principal=principal,
        client_id=client_id,
        secret=secret,
        resource_type=ResourceType.RISK,
        resource_id=risk_id,
    )

    resolver = _get_authorization().resource_resolver
    if not isinstance(resolver, DeveloperResourceResolver):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="developer resource resolver is not configured",
        )

    risk = resolver.risk_repository.get_by_id(risk_id)
    if risk is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="risk not found",
        )

    return _risk_response(risk)
