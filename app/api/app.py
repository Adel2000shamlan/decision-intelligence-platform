from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from uuid import uuid4
import os

from app.infrastructure.database import Database
from app.infrastructure.api_repository import ApiRecordRepository
from app.modules.project.api.router import router as project_router
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
def organization(x: CreateModel):
    o = {"id": str(uuid4()), "name": x.name, "status": "active", "version": 1}
    return records.add("organizations", o)


@router.get("/organizations")
def organizations():
    return records.list("organizations")


@router.post("/projects")
def project(x: CreateModel):
    p = {"id": str(uuid4()), "name": x.name, "status": "draft", "version": 1}
    return records.add("projects", p)


@router.post("/decisions")
def decision(x: DecisionIn):
    d = {"id": str(uuid4()), **x.model_dump(), "status": "draft", "options": [], "scenarios": [], "risks": []}
    return records.add("decisions", d)


@router.post("/decisions/{id}/transition")
def decision_transition(id: str, target: str):
    d = records.get("decisions", id)
    if not d:
        raise HTTPException(404, "decision not found")
    d["status"] = transition("decision", d["status"], target)
    d["version"] += 1
    return d


@router.post("/risks")
def risk(x: RiskIn):
    r = {
        "id": str(uuid4()),
        **x.model_dump(),
        "score": RiskScoreService().calculate(x.probability, x.impact),
        "status": "identified",
    }
    return records.add("risks", r)


@router.get("/risks")
def risks():
    return records.list("risks")


router.include_router(project_router)
