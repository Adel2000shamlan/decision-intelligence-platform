from fastapi import APIRouter
from pydantic import BaseModel, Field
from uuid import uuid4
from app.core.store import store
from app.modules.project.api.router import router as project_router
from app.shared.domain.services import RiskScoreService
router=APIRouter(prefix='/api/v1')
class RiskIn(BaseModel): project_id:str; title:str=Field(min_length=1); probability:float=Field(ge=0,le=1); impact:float=Field(ge=0)
@router.get('/health')
def health(): return {'status':'ok'}
@router.post('/risks')
def risk(x:RiskIn):
    r={'id':str(uuid4()),**x.model_dump(),'score':RiskScoreService().calculate(x.probability,x.impact),'status':'identified'}; return store.add('risks',r)
@router.get('/risks')
def risks(): return store.list('risks')

router.include_router(project_router)
