from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.shared.domain.errors import BusinessRuleViolation, EntityNotFound, InvalidDomainData, InvalidStateTransition

from app.modules.risk.application.commands import (
    AcceptRisk,
    ArchiveRisk,
    AssessRisk,
    CloseRisk,
    CreateRisk,
    IdentifyRisk,
    MonitorRisk,
    RenameRisk,
    RiskCommandHandler,
    StartRiskMitigation,
)
from app.modules.risk.application.ports import RiskUnitOfWork
from app.modules.risk.domain.models import RiskSource
from app.modules.risk.domain.services import RiskPolicyService
from app.modules.risk.in_memory import DefaultRiskFactory, InMemoryRiskRepository


router = APIRouter(prefix="/risks", tags=["risks"])

_repo = InMemoryRiskRepository()
_uow = RiskUnitOfWork(_repo, DefaultRiskFactory(), RiskPolicyService())
_handler = RiskCommandHandler(_uow)


class RiskCreateRequest(BaseModel):
    project_id: UUID
    title: str = Field(min_length=1, max_length=300)
    description: str = ""
    decision_id: UUID | None = None
    source: RiskSource = RiskSource.HUMAN
    actor_id: UUID | None = None


class RiskActionRequest(BaseModel):
    actor_id: UUID | None = None
    expected_version: int | None = Field(default=None, ge=1)


class RiskAssessRequest(RiskActionRequest):
    probability: int = Field(ge=1, le=5)
    impact: int = Field(ge=1, le=5)


class RiskMonitorRequest(RiskActionRequest):
    residual_probability: int = Field(ge=1, le=5)
    residual_impact: int = Field(ge=1, le=5)


class RiskRenameRequest(RiskActionRequest):
    title: str = Field(min_length=1, max_length=300)


def _response(risk):
    return {
        "id": str(risk.id),
        "project_id": str(risk.project_id),
        "title": risk.title,
        "description": risk.description,
        "decision_id": str(risk.decision_id) if risk.decision_id else None,
        "source": risk.source.value,
        "status": risk.status.value,
        "probability": risk.probability,
        "impact": risk.impact,
        "score": risk.score,
        "level": risk.level.value if risk.level else None,
        "residual_probability": risk.residual_probability,
        "residual_impact": risk.residual_impact,
        "residual_score": risk.residual_score,
        "residual_level": risk.residual_level.value if risk.residual_level else None,
        "version": risk.version,
        "created_at": risk.created_at.isoformat(),
        "updated_at": risk.updated_at.isoformat(),
    }


def _error(exc):
    if isinstance(exc, EntityNotFound):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, (BusinessRuleViolation, InvalidStateTransition)):
        return HTTPException(status_code=409, detail=str(exc))
    if isinstance(exc, InvalidDomainData):
        return HTTPException(status_code=400, detail=str(exc))
    return HTTPException(status_code=400, detail=str(exc))


@router.post("")
def create(body: RiskCreateRequest):
    try:
        risk = _handler.create(
            CreateRisk(
                body.project_id,
                body.title,
                body.description,
                body.decision_id,
                body.source,
                body.actor_id,
            )
        )
        return _response(risk)
    except Exception as exc:
        raise _error(exc)


@router.get("/project/{project_id}")
def list_by_project(project_id: UUID):
    return [_response(risk) for risk in _repo.list_by_project(project_id)]


@router.get("/{risk_id}")
def get(risk_id: UUID):
    risk = _repo.get_by_id(risk_id)
    if risk is None:
        raise HTTPException(status_code=404, detail=f"risk not found: {risk_id}")
    return _response(risk)


@router.post("/{risk_id}/identify")
def identify(risk_id: UUID, body: RiskActionRequest):
    try:
        return _response(_handler.identify(IdentifyRisk(risk_id, body.actor_id, body.expected_version)))
    except Exception as exc:
        raise _error(exc)


@router.post("/{risk_id}/assess")
def assess(risk_id: UUID, body: RiskAssessRequest):
    try:
        return _response(_handler.assess(AssessRisk(risk_id, body.probability, body.impact, body.actor_id, body.expected_version)))
    except Exception as exc:
        raise _error(exc)


@router.post("/{risk_id}/mitigation")
def start_mitigation(risk_id: UUID, body: RiskActionRequest):
    try:
        return _response(_handler.start_mitigation(StartRiskMitigation(risk_id, body.actor_id, body.expected_version)))
    except Exception as exc:
        raise _error(exc)


@router.post("/{risk_id}/monitor")
def monitor(risk_id: UUID, body: RiskMonitorRequest):
    try:
        return _response(_handler.monitor(MonitorRisk(risk_id, body.residual_probability, body.residual_impact, body.actor_id, body.expected_version)))
    except Exception as exc:
        raise _error(exc)


@router.post("/{risk_id}/accept")
def accept(risk_id: UUID, body: RiskActionRequest):
    try:
        return _response(_handler.accept(AcceptRisk(risk_id, body.actor_id, body.expected_version)))
    except Exception as exc:
        raise _error(exc)


@router.post("/{risk_id}/close")
def close(risk_id: UUID, body: RiskActionRequest):
    try:
        return _response(_handler.close(CloseRisk(risk_id, body.actor_id, body.expected_version)))
    except Exception as exc:
        raise _error(exc)


@router.post("/{risk_id}/archive")
def archive(risk_id: UUID, body: RiskActionRequest):
    try:
        return _response(_handler.archive(ArchiveRisk(risk_id, body.actor_id, body.expected_version)))
    except Exception as exc:
        raise _error(exc)


@router.patch("/{risk_id}")
def rename(risk_id: UUID, body: RiskRenameRequest):
    try:
        return _response(_handler.rename(RenameRisk(risk_id, body.title, body.actor_id, body.expected_version)))
    except Exception as exc:
        raise _error(exc)
