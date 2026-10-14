from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.modules.business_assessment.application.authorization import (
    BusinessAssessmentAuthorizationAdapter,
    BusinessAssessmentAuthorizationError,
)
from app.modules.business_assessment.application.commands import (
    BusinessAssessmentCommandHandler,
)
from app.modules.business_assessment.application.queries import (
    BusinessAssessmentQueryService,
)
from app.modules.business_assessment.application.service import (
    BusinessAssessmentApplicationFacade,
)
from app.modules.business_assessment.domain.models import (
    BusinessAssessmentStatus,
)
from app.shared.domain.errors import (
    EntityNotFound,
    InvalidDomainData,
)


router = APIRouter(
    prefix="/business-assessments",
    tags=["business-assessments"],
)

_app = None


def configure_repository(repository, organization_repository=None):
    global _app

    _app = BusinessAssessmentApplicationFacade(
        commands=BusinessAssessmentCommandHandler(
            repository,
            organization_repository=organization_repository,
        ),
        queries=BusinessAssessmentQueryService(repository),
        authorization=BusinessAssessmentAuthorizationAdapter(),
    )


class BusinessAssessmentCreateRequest(BaseModel):
    organization_id: UUID
    title: str = Field(min_length=1, max_length=200)
    idea_description: str = Field(default="", max_length=4000)
    actor_id: UUID
    tenant_id: UUID


class BusinessAssessmentActionRequest(BaseModel):
    actor_id: UUID
    tenant_id: UUID
    expected_version: int | None = Field(default=None, ge=1)


class BusinessAssessmentRenameRequest(BusinessAssessmentActionRequest):
    title: str = Field(min_length=1, max_length=200)


def _response(assessment):
    return {
        "id": str(assessment.id),
        "organization_id": str(assessment.organization_id),
        "title": assessment.title,
        "idea_description": assessment.idea_description,
        "status": assessment.status.value,
        "version": assessment.version,
        "created_at": assessment.created_at.isoformat(),
        "updated_at": assessment.updated_at.isoformat(),
    }


def _raise_http(exc):
    if isinstance(exc, EntityNotFound):
        return HTTPException(
            status_code=404,
            detail=str(exc),
        )

    if isinstance(exc, PermissionError):
        return HTTPException(
            status_code=403,
            detail=str(exc),
        )

    if isinstance(exc, (BusinessAssessmentAuthorizationError,)):
        return HTTPException(
            status_code=403,
            detail=str(exc),
        )

    if isinstance(exc, (ValueError, InvalidDomainData)):
        return HTTPException(
            status_code=409,
            detail=str(exc),
        )

    return HTTPException(
        status_code=400,
        detail=str(exc),
    )


def _require_app():
    if _app is None:
        raise HTTPException(
            status_code=503,
            detail="business assessment service is not configured",
        )


@router.post("")
def create(body: BusinessAssessmentCreateRequest):
    _require_app()

    try:
        assessment = _app.create(
            organization_id=body.organization_id,
            title=body.title,
            idea_description=body.idea_description,
            actor_id=body.actor_id,
            tenant_id=body.tenant_id,
        )
        return _response(assessment)
    except Exception as exc:
        raise _raise_http(exc) from exc


@router.get("/organization/{organization_id}")
def list_by_organization(
    organization_id: UUID,
    tenant_id: UUID,
):
    _require_app()

    try:
        return [
            _response(assessment)
            for assessment in _app.list(
                organization_id,
                tenant_id,
            )
        ]
    except Exception as exc:
        raise _raise_http(exc) from exc


@router.get("/organization/{organization_id}/status/{status}")
def list_by_status(
    organization_id: UUID,
    status: BusinessAssessmentStatus,
    tenant_id: UUID,
):
    _require_app()

    try:
        return [
            _response(assessment)
            for assessment in _app.list_by_status(
                organization_id,
                status,
                tenant_id,
            )
        ]
    except Exception as exc:
        raise _raise_http(exc) from exc


@router.get("/{assessment_id}")
def get(
    assessment_id: UUID,
    tenant_id: UUID,
):
    _require_app()

    try:
        return _response(
            _app.get(
                assessment_id,
                tenant_id,
            )
        )
    except Exception as exc:
        raise _raise_http(exc) from exc


@router.post("/{assessment_id}/data-collection")
def start_data_collection(
    assessment_id: UUID,
    body: BusinessAssessmentActionRequest,
):
    _require_app()

    try:
        assessment = _app.start_data_collection(
            assessment_id,
            actor_id=body.actor_id,
            tenant_id=body.tenant_id,
            expected_version=body.expected_version,
        )
        return _response(assessment)
    except Exception as exc:
        raise _raise_http(exc) from exc


@router.post("/{assessment_id}/analysis")
def start_analysis(
    assessment_id: UUID,
    body: BusinessAssessmentActionRequest,
):
    _require_app()

    try:
        assessment = _app.start_analysis(
            assessment_id,
            actor_id=body.actor_id,
            tenant_id=body.tenant_id,
            expected_version=body.expected_version,
        )
        return _response(assessment)
    except Exception as exc:
        raise _raise_http(exc) from exc


@router.post("/{assessment_id}/return-to-data-collection")
def return_to_data_collection(
    assessment_id: UUID,
    body: BusinessAssessmentActionRequest,
):
    _require_app()

    try:
        assessment = _app.return_to_data_collection(
            assessment_id,
            actor_id=body.actor_id,
            tenant_id=body.tenant_id,
            expected_version=body.expected_version,
        )
        return _response(assessment)
    except Exception as exc:
        raise _raise_http(exc) from exc


@router.post("/{assessment_id}/complete")
def complete(
    assessment_id: UUID,
    body: BusinessAssessmentActionRequest,
):
    _require_app()

    try:
        assessment = _app.complete(
            assessment_id,
            actor_id=body.actor_id,
            tenant_id=body.tenant_id,
            expected_version=body.expected_version,
        )
        return _response(assessment)
    except Exception as exc:
        raise _raise_http(exc) from exc


@router.post("/{assessment_id}/archive")
def archive(
    assessment_id: UUID,
    body: BusinessAssessmentActionRequest,
):
    _require_app()

    try:
        assessment = _app.archive(
            assessment_id,
            actor_id=body.actor_id,
            tenant_id=body.tenant_id,
            expected_version=body.expected_version,
        )
        return _response(assessment)
    except Exception as exc:
        raise _raise_http(exc) from exc


@router.patch("/{assessment_id}")
def update_title(
    assessment_id: UUID,
    body: BusinessAssessmentRenameRequest,
):
    _require_app()

    try:
        assessment = _app.update_title(
            assessment_id,
            body.title,
            actor_id=body.actor_id,
            tenant_id=body.tenant_id,
            expected_version=body.expected_version,
        )
        return _response(assessment)
    except Exception as exc:
        raise _raise_http(exc) from exc
