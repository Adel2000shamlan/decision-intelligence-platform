from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from hashlib import pbkdf2_hmac
from hmac import compare_digest
import base64, hashlib, secrets
from typing import Iterable
from uuid import UUID, uuid4

class SecurityError(Exception): pass
class PasswordPolicyError(SecurityError): pass
class CredentialError(SecurityError): pass
class TokenError(SecurityError): pass
class AuthorizationError(SecurityError): pass

class CredentialStatus(str, Enum): ACTIVE='active'; REVOKED='revoked'; COMPROMISED='compromised'; EXPIRED='expired'
@dataclass(frozen=True)
class PasswordSecurityPolicy:
    min_length:int=12; max_length:int=128; iterations:int=310_000; salt_bytes:int=16
    def validate(self,password:str)->None:
        if not isinstance(password,str): raise PasswordPolicyError('password must be text')
        if not self.min_length <= len(password) <= self.max_length: raise PasswordPolicyError('password length violates policy')
        if password.strip()!=password: raise PasswordPolicyError('password cannot begin or end with whitespace')
        if not any(c.islower() for c in password) or not any(c.isupper() for c in password) or not any(c.isdigit() for c in password): raise PasswordPolicyError('password must contain upper, lower and digit')

@dataclass(frozen=True)
class PasswordHash:
    algorithm:str; iterations:int; salt:str; digest:str
    def encoded(self): return f'{self.algorithm}${self.iterations}${self.salt}${self.digest}'

class PasswordHasher:
    algorithm='pbkdf2_sha256'
    def __init__(self, policy:PasswordSecurityPolicy|None=None): self.policy=policy or PasswordSecurityPolicy()
    def hash(self,password:str)->PasswordHash:
        self.policy.validate(password); salt=secrets.token_bytes(self.policy.salt_bytes)
        d=pbkdf2_hmac('sha256',password.encode(),salt,self.policy.iterations)
        return PasswordHash(self.algorithm,self.policy.iterations,base64.urlsafe_b64encode(salt).decode(),base64.urlsafe_b64encode(d).decode())
    def verify(self,password:str,stored:PasswordHash)->bool:
        try:
            if stored.algorithm!=self.algorithm: return False
            salt=base64.urlsafe_b64decode(stored.salt.encode()); d=pbkdf2_hmac('sha256',password.encode(),salt,stored.iterations)
            return compare_digest(base64.urlsafe_b64encode(d).decode(),stored.digest)
        except Exception: return False

@dataclass
class CredentialRecord:
    id:UUID; user_id:UUID; password_hash:PasswordHash; status:CredentialStatus=CredentialStatus.ACTIVE
    created_at:datetime=field(default_factory=lambda:datetime.now(timezone.utc)); updated_at:datetime=field(default_factory=lambda:datetime.now(timezone.utc)); version:int=1; compromised_at:datetime|None=None

class CredentialRepository:
    def __init__(self): self.items={}; self.history=[]
    def active(self,user_id): return next((c for c in self.items.values() if c.user_id==user_id and c.status is CredentialStatus.ACTIVE),None)
    def add(self,c):
        if self.active(c.user_id): raise CredentialError('active credential already exists')
        self.items[c.id]=c
    def replace(self,c): self.items[c.id]=c
    def revoke_user(self,user_id,status=CredentialStatus.REVOKED):
        c=self.active(user_id)
        if c: c.status=status; c.version+=1; c.updated_at=datetime.now(timezone.utc); self.history.append(c.id)
        return c

@dataclass(frozen=True)
class SecurityEvent:
    name:str; user_id:UUID|None; actor_id:UUID|None; correlation_id:UUID; occurred_at:datetime=field(default_factory=lambda:datetime.now(timezone.utc)); metadata:tuple[tuple[str,str],...]=()
class AuditLog:
    def __init__(self): self.events=[]
    def emit(self,event): self.events.append(event)

class CredentialService:
    def __init__(self,repo=None,hasher=None,policy=None,audit=None):
        self.repo=repo or CredentialRepository(); self.policy=policy or PasswordSecurityPolicy(); self.hasher=hasher or PasswordHasher(self.policy); self.audit=audit or AuditLog(); self.history={} 
    def register(self,user_id,password,actor_id=None,correlation_id=None):
        if self.repo.active(user_id): raise CredentialError('credential already registered')
        self.policy.validate(password)
        if any(self.hasher.verify(password, old) for old in self.history.get(user_id, [])): raise PasswordPolicyError('password reuse is forbidden')
        c=CredentialRecord(uuid4(),user_id,self.hasher.hash(password)); self.repo.add(c); self.history.setdefault(user_id,[]).append(c.password_hash); self.history[user_id]=self.history[user_id][-5:]; self.audit.emit(SecurityEvent('credential.created',user_id,actor_id,correlation_id or uuid4())); return c
    def verify(self,user_id,password,actor_id=None,correlation_id=None):
        c=self.repo.active(user_id); ok=bool(c and self.hasher.verify(password,c.password_hash))
        self.audit.emit(SecurityEvent('credential.verified' if ok else 'credential.verification_failed',user_id,actor_id,correlation_id or uuid4()))
        return ok
    def change(self,user_id,current_password,new_password,actor_id=None,correlation_id=None):
        if not self.verify(user_id,current_password,actor_id,correlation_id): raise CredentialError('current credential invalid')
        c=self.repo.active(user_id); assert c
        self.policy.validate(new_password)
        if any(self.hasher.verify(new_password, old) for old in self.history.get(user_id, [])): raise PasswordPolicyError('password reuse is forbidden')
        c.password_hash=self.hasher.hash(new_password); self.history.setdefault(user_id,[]).append(c.password_hash); self.history[user_id]=self.history[user_id][-5:]; c.version+=1; c.updated_at=datetime.now(timezone.utc); self.audit.emit(SecurityEvent('credential.rotated',user_id,actor_id,correlation_id or uuid4())); return c
    def compromise(self,user_id,actor_id=None,correlation_id=None):
        c=self.repo.revoke_user(user_id,CredentialStatus.COMPROMISED)
        if c: c.compromised_at=datetime.now(timezone.utc)
        self.audit.emit(SecurityEvent('credential.compromised',user_id,actor_id,correlation_id or uuid4())); return c
    def revoke(self,user_id,actor_id=None,correlation_id=None):
        c=self.repo.revoke_user(user_id); self.audit.emit(SecurityEvent('credential.revoked',user_id,actor_id,correlation_id or uuid4())); return c

class ResetRepository:
    def __init__(self): self.items={}
    def issue(self,user_id,ttl_minutes=15):
        raw=secrets.token_urlsafe(32); key=hashlib.sha256(raw.encode()).hexdigest(); self.items[key]=(user_id,datetime.now(timezone.utc)+timedelta(minutes=ttl_minutes),False); return raw
    def consume(self,raw):
        key=hashlib.sha256(raw.encode()).hexdigest(); item=self.items.get(key)
        if not item or item[2] or item[1] < datetime.now(timezone.utc): raise CredentialError('invalid or expired reset token')
        self.items[key]=(item[0],item[1],True); return item[0]

class TokenType(str,Enum): ACCESS='access'; REFRESH='refresh'
@dataclass(frozen=True)
class TokenRecord:
    token_id:UUID; user_id:UUID; token_type:TokenType; issued_at:datetime; expires_at:datetime; session_id:UUID; revoked:bool=False; tenant_id:UUID|None=None; roles:tuple[str,...]=()
class TokenService:
    def __init__(self,access_minutes=15,refresh_days=30): self.tokens={}; self.access_minutes=access_minutes; self.refresh_days=refresh_days
    def issue(self,user_id,tenant_id=None,roles=()):
        sid=uuid4(); now=datetime.now(timezone.utc); out=[]
        for typ,delta in ((TokenType.ACCESS,timedelta(minutes=self.access_minutes)),(TokenType.REFRESH,timedelta(days=self.refresh_days))):
            raw=secrets.token_urlsafe(48); tid=uuid4(); self.tokens[hashlib.sha256(raw.encode()).hexdigest()]=TokenRecord(tid,user_id,typ,now,now+delta,sid,False,tenant_id,tuple(roles)); out.append(raw)
        return out[0],out[1]
    def validate(self,raw,expected=TokenType.ACCESS):
        r=self.tokens.get(hashlib.sha256(raw.encode()).hexdigest()); now=datetime.now(timezone.utc)
        if not r or r.revoked or r.expires_at<=now or r.token_type is not expected: raise TokenError('invalid token')
        return r
    def refresh(self,raw):
        r=self.validate(raw,TokenType.REFRESH)
        self.revoke(raw)
        return self.issue(r.user_id,r.tenant_id,r.roles)[0]

    def revoke(self,raw):
        k=hashlib.sha256(raw.encode()).hexdigest(); r=self.tokens.get(k)
        if r: self.tokens[k]=TokenRecord(r.token_id,r.user_id,r.token_type,r.issued_at,r.expires_at,r.session_id,True,r.tenant_id,r.roles)
    def revoke_session(self,session_id):
        for k,r in list(self.tokens.items()):
            if r.session_id==session_id: self.tokens[k]=TokenRecord(r.token_id,r.user_id,r.token_type,r.issued_at,r.expires_at,r.session_id,True,r.tenant_id,r.roles)

@dataclass(frozen=True)
class Role: name:str; permissions:frozenset[str]
class RBAC:
    def __init__(self): self.roles={}; self.assignments={}; self.tenants={}
    def define(self,role,permissions): self.roles[role]=Role(role,frozenset(permissions))
    def assign(self,user_id,role,tenant_id):
        if role not in self.roles: raise AuthorizationError('unknown role')
        self.assignments.setdefault((user_id,tenant_id),set()).add(role)
    def permissions(self,user_id,tenant_id):
        out=set()
        for r in self.assignments.get((user_id,tenant_id),set()): out |= set(self.roles[r].permissions)
        return frozenset(out)
    def require(self,user_id,tenant_id,permission):
        if permission not in self.permissions(user_id,tenant_id): raise AuthorizationError('permission denied')

@dataclass(frozen=True)
class AuthSession:
    user_id:UUID; tenant_id:UUID|None; session_id:UUID; roles:tuple[str,...]; authenticated_at:datetime; assurance_level:str='standard'
class AuthenticationService:
    def __init__(self,users,credentials=None,tokens=None,rbac=None): self.users=users; self.credentials=credentials or CredentialService(); self.tokens=tokens or TokenService(); self.rbac=rbac or RBAC()
    def login(self,email,password,tenant_id=None):
        user=self.users.get_by_email(email)
        if not user or not user.is_active or not self.credentials.verify(user.id,password): raise CredentialError('invalid credentials')
        roles=tuple(self.rbac.assignments.get((user.id,tenant_id),set())) if tenant_id else ()
        a,r=self.tokens.issue(user.id,tenant_id,roles); rec=self.tokens.validate(a); return AuthSession(user.id,tenant_id,rec.session_id,roles,datetime.now(timezone.utc)),a,r

class PasswordResetService:
    def __init__(self,credentials,reset_repo=None,audit=None): self.credentials=credentials; self.reset=reset_repo or ResetRepository(); self.audit=audit or credentials.audit
    def request(self,user_id):
        return self.reset.issue(user_id)
    def consume(self,token,new_password,actor_id=None):
        uid=self.reset.consume(token); c=self.credentials.repo.active(uid)
        if c:
            self.credentials.policy.validate(new_password)
            if any(self.credentials.hasher.verify(new_password, old) for old in self.credentials.history.get(uid,[])): raise PasswordPolicyError('password reuse is forbidden')
            c.password_hash=self.credentials.hasher.hash(new_password); c.version+=1; c.updated_at=datetime.now(timezone.utc)
            self.credentials.history.setdefault(uid,[]).append(c.password_hash); self.credentials.history[uid]=self.credentials.history[uid][-5:]
            self.audit.emit(SecurityEvent('password.reset_completed',uid,actor_id,uuid4())); return uid
        self.credentials.register(uid,new_password,actor_id); self.audit.emit(SecurityEvent('password.reset_completed',uid,actor_id,uuid4())); return uid

class RecoveryService:
    def __init__(self,credentials,reset_repo=None,audit=None): self.credentials=credentials; self.reset=reset_repo or ResetRepository(); self.audit=audit or credentials.audit
    def request(self,user_id):
        raw=self.reset.issue(user_id); self.audit.emit(SecurityEvent('password.reset_requested',user_id,None,uuid4())); return raw
    def consume(self,token,new_password,actor_id=None):
        uid=self.reset.consume(token); self.credentials.register(uid,new_password,actor_id); self.audit.emit(SecurityEvent('password.reset_completed',uid,actor_id,uuid4())); return uid

@dataclass(frozen=True)
class SecurityPolicy:
    max_sessions:int=5; access_minutes:int=15; refresh_days:int=30; reset_minutes:int=15; require_mfa_for_strong_assurance:bool=False
    def validate(self):
        if self.max_sessions<1 or self.access_minutes<1 or self.refresh_days<1 or self.reset_minutes<1: raise ValueError('invalid security policy')
