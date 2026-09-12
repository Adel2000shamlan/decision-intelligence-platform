from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from uuid import uuid4
from app.core.store import store
from app.modules.project.api.router import router as project_router
from app.shared.domain.state_machine import transition
from app.shared.domain.services import RiskScoreService
router=APIRouter(prefix='/api/v1')
class CreateModel(BaseModel): name:str=Field(min_length=1,max_length=200)
class DecisionIn(BaseModel): project_id:str; title:str=Field(min_length=1); objective:str=Field(min_length=1)
class RiskIn(BaseModel): project_id:str; title:str=Field(min_length=1); probability:float=Field(ge=0,le=1); impact:float=Field(ge=0)
@router.get('/health')
def health(): return {'status':'ok'}
@router.post('/organizations')
def organization(x:CreateModel):
    o={'id':str(uuid4()),'name':x.name,'status':'active','version':1}; return store.add('organizations',o)
@router.get('/organizations')
def organizations(): return store.list('organizations')
@router.post('/projects')
def project(x:CreateModel):
    p={'id':str(uuid4()),'name':x.name,'status':'draft','version':1}; return store.add('projects',p)
@router.post('/decisions')
def decision(x:DecisionIn):
    d={'id':str(uuid4()),**x.model_dump(),'status':'draft','options':[],'scenarios':[],'risks':[]}; return store.add('decisions',d)
@router.post('/decisions/{id}/transition')
def decision_transition(id:str,target:str):
    d=store.get('decisions',id)
    if not d: raise HTTPException(404,'decision not found')
    d['status']=transition('decision',d['status'],target); d['version']+=1; return d
@router.post('/risks')
def risk(x:RiskIn):
    r={'id':str(uuid4()),**x.model_dump(),'score':RiskScoreService().calculate(x.probability,x.impact),'status':'identified'}; return store.add('risks',r)
@router.get('/risks')
def risks(): return store.list('risks')

router.include_router(project_router)
