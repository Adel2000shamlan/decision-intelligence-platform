from dataclasses import dataclass, field
import time, threading, re
@dataclass(frozen=True)
class GatewayRequest:
    method:str; path:str; actor_id:str|None; tenant_id:str|None; body:dict
@dataclass(frozen=True)
class GatewayResponse:
    allowed:bool; reason:str
class RateLimiter:
    def __init__(self,limit=60,window=60): self.limit=limit; self.window=window; self._hits={}; self._lock=threading.RLock()
    def allow(self,key):
        now=time.monotonic()
        with self._lock:
            hits=[t for t in self._hits.get(key,[]) if t>now-self.window]
            if len(hits)>=self.limit:self._hits[key]=hits;return False
            hits.append(now);self._hits[key]=hits;return True
class APIGateway:
    def __init__(self,rate=None,authorize=None): self.rate=rate or RateLimiter(); self.authorize=authorize
    def validate(self,r):
        if r.method.upper() not in {'GET','POST','PUT','PATCH','DELETE'}: raise ValueError('unsupported HTTP method')
        if not re.fullmatch(r'/api/v1(?:/.*)?',r.path): raise ValueError('unsupported API version')
        if not r.tenant_id: raise PermissionError('tenant context required')
        if not self.rate.allow(r.tenant_id): raise PermissionError('rate limit exceeded')
        if self.authorize and not self.authorize(r): raise PermissionError('authorization denied')
        return True
