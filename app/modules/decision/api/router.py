from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.modules.decision.application.implementation import DecisionApplicationService
from app.modules.decision.domain.models import DecisionPriority, DecisionType
from app.shared.domain.errors import BusinessRuleViolation, EntityNotFound, InvalidDomainData


router = APIRouter(prefix="/decisions", tags=["decisions"])

_app = DecisionApplicationService.in_memory()


class DecisionCreateRequest(BaseModel):
    organization_id: UUID
    project_id: UUID
    title: str = Field(min_length=1)
    description: str = ""
    decision_type: DecisionType = DecisionType.STRATEGIC
    priority: DecisionPriority = DecisionPriority.MEDIUM
    actor_id: UUID | None = None


class DecisionActionRequest(BaseModel):
    actor_id: UUID | None = None
    reason: str | None = None
    expected_version: int | None = None


def _response(decision):
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


def _get(decision_id: UUID):
    decision = _app.get(decision_id)
    if decision is None:
        raise HTTPException(status_code=404, detail="decision not found")
    return decision


@router.post("")
def create(body: DecisionCreateRequest):
    try:
        decision = _app.create(
            organization_id=body.organization_id,
            project_id=body.project_id,
            title=body.title,
            description=body.description,
            decision_type=body.decision_type,
            priority=body.priority,
            actor_id=body.actor_id,
        )
    except (BusinessRuleViolation, InvalidDomainData) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _response(decision)


@router.get("/{decision_id}")
def get(decision_id: UUID):
    return _response(_get(decision_id))


@router.post("/{decision_id}/analysis")
def start_analysis(decision_id: UUID, body: DecisionActionRequest):
    _get(decision_id)
    try:
        decision = _app.start_analysis(
            decision_id,
            actor_id=body.actor_id,
            expected_version=body.expected_version,
        )
    except (BusinessRuleViolation, InvalidDomainData) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _response(decision)


@router.post("/{decision_id}/submit")
def submit_for_approval(decision_id: UUID, body: DecisionActionRequest):
    _get(decision_id)
    try:
        decision = _app.submit_for_approval(
            decision_id,
            actor_id=body.actor_id,
            expected_version=body.expected_version,
        )
    except (BusinessRuleViolation, InvalidDomainData) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _response(decision)


@router.post("/{decision_id}/approve")
def approve(decision_id: UUID, body: DecisionActionRequest):
    _get(decision_id)
    try:
        decision = _app.approve(
            decision_id,
            actor_id=body.actor_id,
            expected_version=body.expected_version,
        )
    except (BusinessRuleViolation, InvalidDomainData) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _response(decision)


@router.post("/{decision_id}/reject")
def reject(decision_id: UUID, body: DecisionActionRequest):
    _get(decision_id)
    try:
        decision = _app.reject(
            decision_id,
            reason=body.reason,
            actor_id=body.actor_id,
            expected_version=body.expected_version,
        )
    except (BusinessRuleViolation, InvalidDomainData) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _response(decision)


@router.post("/{decision_id}/cancel")
def cancel(decision_id: UUID, body: DecisionActionRequest):
    _get(decision_id)
    try:
        decision = _app.cancel(
            decision_id,
            reason=body.reason,
            actor_id=body.actor_id,
            expected_version=body.expected_version,
        )
    except (BusinessRuleViolation, InvalidDomainData) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _response(decision)


@router.post("/{decision_id}/execute")
def execute(decision_id: UUID, body: DecisionActionRequest):
    _get(decision_id)
    try:
        decision = _app.execute(
            decision_id,
            actor_id=body.actor_id,
            expected_version=body.expected_version,
        )
    except (BusinessRuleViolation, InvalidDomainData) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _response(decision)


@router.post("/{decision_id}/close")
def close(decision_id: UUID, body: DecisionActionRequest):
    _get(decision_id)
    try:
        decision = _app.close(
            decision_id,
            actor_id=body.actor_id,
            expected_version=body.expected_version,
        )
    except (BusinessRuleViolation, InvalidDomainData) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _response(decision)
