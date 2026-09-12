from uuid import UUID
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from app.modules.organization.persistence.sqlite import SQLiteOrganizationRepository
from app.modules.organization.application.service import OrganizationApplicationService
router=APIRouter(prefix='/organizations',tags=['organizations'])
_repo=SQLiteOrganizationRepository(); _service=OrganizationApplicationService(_repo)
class OrganizationCreateRequest(BaseModel): name:str=Field(min_length=1,max_length=200); slug:str=Field(min_length=1,max_length=100)
@router.post('')
def create(req:OrganizationCreateRequest):
    try:
        o=_service.create(req.name,req.slug)
        return {'id':str(o.id),'name':o.name,'slug':o.slug,'status':o.status.value,'version':o.version}
    except Exception as e: raise HTTPException(400,str(e))
@router.get('/{organization_id}')
def get(organization_id:UUID):
    try:o=_service.get(organization_id); return {'id':str(o.id),'name':o.name,'slug':o.slug,'status':o.status.value,'version':o.version}
    except Exception as e: raise HTTPException(404,str(e))
