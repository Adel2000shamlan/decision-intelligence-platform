from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from uuid import uuid4
import os

from app.infrastructure.database import Database
from app.infrastructure.api_repository import ApiRecordRepository
from uuid import UUID
from app.modules.project.api.router import router as project_router, _app as project_application
from app.modules.authentication.dependencies import require_permission
from app.shared.domain.errors import EntityNotFound, InvalidStateTransition
from app.shared.domain.state_machine import transition
from app.shared.domain.services import RiskScoreService

router = APIRouter(prefix="/api/v1")
records = ApiRecordRepository()


class CreateModel(BaseModel):
    name: str = Field(min_length=1, max_length=200)


class DecisionIn(BaseModel):
    project_id: str
    title: str = Field(min_length=1)
    objective: str = Field(min_length=1)


class RiskIn(BaseModel):
    project_id: str
    title: str = Field(min_length=1)
    probability: float = Field(ge=0, le=1)
    impact: float = Field(ge=0)


@router.get("/health")
def health():
    """Liveness only: confirms the API process can answer HTTP requests."""
    return {"status": "ok"}


@router.get("/ready")
def readiness():
    """Check configured PostgreSQL and Redis dependencies before receiving traffic."""
    checks = {}
    try:
        database_url = os.getenv("DATABASE_URL")
        if not database_url or not database_url.startswith(("postgresql://", "postgres://")):
            raise RuntimeError("DATABASE_URL must point to PostgreSQL in production")
        with Database(database_url).transaction() as conn:
            conn.execute("SELECT 1")
        checks["database"] = "ok"
    except Exception:
        checks["database"] = "error"

    try:
        redis_url = os.getenv("REDIS_URL")
        if not redis_url:
            raise RuntimeError("REDIS_URL is required in production")
        from redis import Redis
        client = Redis.from_url(redis_url, socket_connect_timeout=2, socket_timeout=2)
        client.ping()
        client.close()
        checks["redis"] = "ok"
    except Exception:
        checks["redis"] = "error"

    if any(status != "ok" for status in checks.values()):
        raise HTTPException(status_code=503, detail={"status": "not_ready", "checks": checks})
    return {"status": "ready", "checks": checks}


@router.post("/organizations")
def organization(x: CreateModel, principal=Depends(require_permission("user:manage"))):
    o = {
        "id": str(uuid4()),
        "tenant_id": str(principal.tenant_id),
        "name": x.name,
        "status": "active",
        "version": 1,
    }
    return records.add("organizations", o)


@router.get("/organizations")
def organizations(principal=Depends(require_permission("user:manage"))):
    tenant_id = str(principal.tenant_id)
    return records.list_for_tenant("organizations", tenant_id)


def _require_project_tenant(project_id: str, principal):
    try:
        project_application.get(UUID(project_id), tenant_id=principal.tenant_id)
    except (EntityNotFound, ValueError, TypeError) as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc


@router.post("/decisions")
def decision(x: DecisionIn, principal=Depends(require_permission("decision:write"))):
    _require_project_tenant(x.project_id, principal)
    d = {
        "id": str(uuid4()),
        **x.model_dump(),
        "tenant_id": str(principal.tenant_id),
        "status": "draft",
        "version": 1,
        "options": [],
        "scenarios": [],
        "risks": [],
    }
    return records.add("decisions", d)


@router.post("/decisions/{id}/transition")
def decision_transition(
    id: str,
    target: str,
    principal=Depends(require_permission("decision:write")),
):
    d = records.get_for_tenant("decisions", id, principal.tenant_id)
    if not d:
        raise HTTPException(status_code=404, detail="Decision not found")
    try:
        next_status = transition("decision", d["status"], target)
    except InvalidStateTransition as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    d["status"] = next_status
    d["version"] = d.get("version", 1) + 1
    try:
        return records.update_for_tenant("decisions", d, principal.tenant_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Decision not found") from exc


@router.post("/risks")
def risk(x: RiskIn, principal=Depends(require_permission("decision:write"))):
    _require_project_tenant(x.project_id, principal)
    r = {
        "id": str(uuid4()),
        **x.model_dump(),
        "tenant_id": str(principal.tenant_id),
        "score": RiskScoreService().calculate(x.probability, x.impact),
        "status": "identified",
    }
    return records.add("risks", r)


@router.get("/risks")
def risks(principal=Depends(require_permission("decision:read"))):
    tenant_id = str(principal.tenant_id)
    return records.list_for_tenant("risks", tenant_id)


router.include_router(project_router)
