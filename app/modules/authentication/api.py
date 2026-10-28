from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel, Field
from uuid import UUID
from app.modules.identity.in_memory import InMemoryUserRepository
from .security import *
router=APIRouter(prefix='/auth',tags=['authentication'])
users=InMemoryUserRepository(); credentials=CredentialService(); tokens=TokenService(); rbac=RBAC(); auth=AuthenticationService(users,credentials,tokens,rbac); password_resets=PasswordResetService(credentials,tokens=tokens)
rbac.define('owner',{'decision:read','decision:write','project:read','project:write','user:manage'}); rbac.define('viewer',{'decision:read','project:read'})
class RegisterIn(BaseModel): user_id:UUID; password:str=Field(min_length=1)
class LoginIn(BaseModel): email:str; password:str; tenant_id:UUID|None=None
class ChangeIn(BaseModel): current_password:str; new_password:str
class ResetIn(BaseModel): user_id:UUID
class ResetConsumeIn(BaseModel): token:str; new_password:str
@router.post('/credentials/register')
def register(x:RegisterIn):
    try: return {'credential_id':str(credentials.register(x.user_id,x.password).id)}
    except SecurityError as e: raise HTTPException(400,str(e))
@router.post('/login')
def login(x:LoginIn):
    try:
        s,a,r=auth.login(x.email,x.password,x.tenant_id); return {'access_token':a,'refresh_token':r,'token_type':'bearer','user_id':str(s.user_id),'session_id':str(s.session_id)}
    except SecurityError as e: raise HTTPException(401,str(e))
@router.post('/change-password')
def change(x:ChangeIn,authorization:str=Header(default='')):
    try:
        raw=authorization.strip().split(None, 1)[-1] if authorization.strip().lower().startswith('bearer ') else authorization.strip(); rec=tokens.validate(raw); c=credentials.change(rec.user_id,x.current_password,x.new_password,rec.user_id); tokens.revoke_session(rec.session_id); return {'credential_version':c.version}
    except SecurityError as e: raise HTTPException(401,str(e))
@router.post('/logout')
def logout(authorization:str=Header(default='')):
    try: rec=tokens.validate(authorization.strip().split(None, 1)[-1] if authorization.strip().lower().startswith('bearer ') else authorization.strip()); tokens.revoke_session(rec.session_id); return {'logged_out':True}
    except SecurityError as e: raise HTTPException(401,str(e))
@router.post('/password-reset/request')
def reset_request(x:ResetIn):
    token = password_resets.request(x.user_id)
    from app.infrastructure.config import settings
    response = {'accepted': True}
    if settings.environment.strip().lower() == 'development':
        response['reset_token'] = token
    return response
@router.post('/password-reset/consume')
def reset_consume(x:ResetConsumeIn):
    try: uid=password_resets.consume(x.token,x.new_password); return {'reset':True,'user_id':str(uid)}
    except SecurityError as e: raise HTTPException(400,str(e))

class RefreshIn(BaseModel): refresh_token:str
@router.post('/refresh')
def refresh(x:RefreshIn):
    try:
        record = tokens.validate(x.refresh_token, TokenType.REFRESH)
        current_roles = tuple(sorted(
            rbac.assignments.get((record.user_id, record.tenant_id), set())
        )) if record.tenant_id is not None else ()
        if record.tenant_id is not None and not current_roles:
            tokens.revoke(x.refresh_token)
            raise HTTPException(403, "No role assigned for this tenant")
        return tokens.refresh(x.refresh_token, roles=current_roles)
    except SecurityError as e:
        raise HTTPException(401, str(e))
