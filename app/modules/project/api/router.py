from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.modules.authentication.dependencies import require_permission
from app.modules.project.application.commands import ProjectCommandHandler
from app.modules.project.application.queries import ProjectQueryService
from app.modules.project.application.repository import ProjectRepositoryAdapter
from app.modules.project.application.service import ProjectApplicationFacade
from app.modules.project.application.tenant import ProjectTenantGuard
from app.infrastructure.config import settings
from app.modules.project.persistence.sqlite import SQLiteProjectRepository
from app.modules.project.persistence.postgres import PostgreSQLProjectRepository
from app.shared.domain.errors import EntityNotFound


router = APIRouter(prefix="/projects", tags=["projects"])

_database_url = settings.database_url
if _database_url.startswith(("postgresql://", "postgres://")):
    _backend = PostgreSQLProjectRepository(_database_url)
else:
    _sqlite_path = _database_url.removeprefix("sqlite:///")
    _backend = SQLiteProjectRepository(path=_sqlite_path)

_repo = ProjectRepositoryAdapter(_backend)
_app = ProjectApplicationFacade(
    ProjectCommandHandler(_repo, tenant_guard=ProjectTenantGuard()),
    ProjectQueryService(_repo),
)


class ProjectCreateRequest(BaseModel):
    organization_id: UUID
    name: str


class ProjectRenameRequest(BaseModel):
    name: str
    expected_version: int | None = None


class ProjectTransitionRequest(BaseModel):
    status: str
    expected_version: int | None = None


def _serialize(project):
    return {
        "id": str(project.id),
        "organization_id": str(project.organization_id),
        "name": project.name,
        "status": project.status.value,
        "version": project.version,
    }


def _check_tenant(principal, organization_id):
    if principal.tenant_id is None:
        raise HTTPException(403, "Tenant context required")
    if principal.tenant_id != organization_id:
        raise HTTPException(403, "Tenant boundary violation")


@router.post("")
def create(
    body: ProjectCreateRequest,
    principal=Depends(require_permission("project:write")),
):
    _check_tenant(principal, body.organization_id)
    try:
        project = _app.create(
            body.organization_id,
            body.name,
            actor_id=principal.user_id,
            tenant_id=principal.tenant_id,
        )
        return _serialize(project)
    except HTTPException:
        raise
    except PermissionError as exc:
        raise HTTPException(403, "Tenant boundary violation") from exc
    except (ValueError, TypeError) as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("/organization/{organization_id}")
def list_projects(
    organization_id: UUID,
    principal=Depends(require_permission("project:read")),
):
    _check_tenant(principal, organization_id)
    return [
        _serialize(project)
        for project in _app.list(
            organization_id,
            tenant_id=principal.tenant_id,
        )
    ]


@router.get("/{project_id}")
def get(
    project_id: UUID,
    principal=Depends(require_permission("project:read")),
):
    try:
        project = _app.get(project_id, tenant_id=principal.tenant_id)
        return _serialize(project)
    except EntityNotFound as exc:
        raise HTTPException(404, "Project not found") from exc
    except PermissionError as exc:
        raise HTTPException(403, "Tenant boundary violation") from exc


@router.patch("/{project_id}")
def rename(
    project_id: UUID,
    body: ProjectRenameRequest,
    principal=Depends(require_permission("project:write")),
):
    try:
        project = _app.rename(
            project_id,
            body.name,
            actor_id=principal.user_id,
            tenant_id=principal.tenant_id,
            expected_version=body.expected_version,
        )
        return _serialize(project)
    except EntityNotFound as exc:
        raise HTTPException(404, "Project not found") from exc
    except PermissionError as exc:
        raise HTTPException(403, "Tenant boundary violation") from exc
    except (ValueError, TypeError) as exc:
        raise HTTPException(400, str(exc)) from exc

@router.post("/{project_id}/transition")
def transition(
    project_id: UUID,
    body: ProjectTransitionRequest,
    principal=Depends(require_permission("project:write")),
):
    try:
        project = _app.transition(
            project_id,
            body.status,
            actor_id=principal.user_id,
            tenant_id=principal.tenant_id,
            expected_version=body.expected_version,
        )
        return _serialize(project)
    except EntityNotFound as exc:
        raise HTTPException(404, "Project not found") from exc
    except PermissionError as exc:
        raise HTTPException(403, "Tenant boundary violation") from exc
    except (ValueError, TypeError) as exc:
        raise HTTPException(400, str(exc)) from exc
