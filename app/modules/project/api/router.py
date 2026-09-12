from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from uuid import UUID
from app.modules.project.persistence.sqlite import SQLiteProjectRepository
from app.modules.project.application.repository import ProjectRepositoryAdapter
from app.modules.project.application.queries import ProjectQueryService
from app.modules.project.application.commands import ProjectCommandHandler
from app.modules.project.application.service import ProjectApplicationFacade

router=APIRouter(prefix='/projects',tags=['projects'])
_repo=ProjectRepositoryAdapter(SQLiteProjectRepository())
_app=ProjectApplicationFacade(ProjectCommandHandler(_repo),ProjectQueryService(_repo))
class ProjectCreateRequest(BaseModel): organization_id: UUID; name: str
class ProjectRenameRequest(BaseModel): name: str; expected_version: int|None=None
class ProjectTransitionRequest(BaseModel): status: str; expected_version: int|None=None
@router.post('')
def create(body:ProjectCreateRequest):
    try: p=_app.create(body.organization_id,body.name)
    except Exception as e: raise HTTPException(400,str(e))
    return {'id':str(p.id),'organization_id':str(p.organization_id),'name':p.name,'status':p.status.value,'version':p.version}
@router.get('/organization/{organization_id}')
def list_projects(organization_id:UUID):
    return [{'id':str(p.id),'organization_id':str(p.organization_id),'name':p.name,'status':p.status.value,'version':p.version} for p in _app.list(organization_id)]
@router.patch('/{project_id}')
def rename(project_id:UUID, body:ProjectRenameRequest):
    try: p=_app.rename(project_id,body.name,expected_version=body.expected_version)
    except Exception as e: raise HTTPException(400,str(e))
    return {'id':str(p.id),'organization_id':str(p.organization_id),'name':p.name,'status':p.status.value,'version':p.version}
@router.post('/{project_id}/transition')
def transition(project_id:UUID, body:ProjectTransitionRequest):
    try: p=_app.transition(project_id,body.status,expected_version=body.expected_version)
    except Exception as e: raise HTTPException(400,str(e))
    return {'id':str(p.id),'organization_id':str(p.organization_id),'name':p.name,'status':p.status.value,'version':p.version}
@router.get('/{project_id}')
def get(project_id:UUID):
    try:p=_app.get(project_id)
    except Exception as e: raise HTTPException(404,str(e))
    return {'id':str(p.id),'organization_id':str(p.organization_id),'name':p.name,'status':p.status.value,'version':p.version}
