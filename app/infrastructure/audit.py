from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib, json
@dataclass(frozen=True)
class AuditRecord:
    sequence:int; action:str; actor_id:str|None; subject_id:str|None; occurred_at:datetime; payload:dict; previous_hash:str; record_hash:str
class TamperEvidentAudit:
    def __init__(self): self.records=[]
    def append(self,action,actor_id,subject_id,payload=None):
        payload=dict(payload or {}); prev=self.records[-1].record_hash if self.records else 'GENESIS'; seq=len(self.records)+1; now=datetime.now(timezone.utc); raw=json.dumps({'sequence':seq,'action':action,'actor_id':str(actor_id) if actor_id else None,'subject_id':str(subject_id) if subject_id else None,'occurred_at':now.isoformat(),'payload':payload,'previous_hash':prev},sort_keys=True,separators=(',',':')).encode(); h=hashlib.sha256(raw).hexdigest(); self.records.append(AuditRecord(seq,action,str(actor_id) if actor_id else None,str(subject_id) if subject_id else None,now,payload,prev,h)); return self.records[-1]
    def verify(self):
        prev='GENESIS'
        for r in self.records:
            raw=json.dumps({'sequence':r.sequence,'action':r.action,'actor_id':r.actor_id,'subject_id':r.subject_id,'occurred_at':r.occurred_at.isoformat(),'payload':r.payload,'previous_hash':r.previous_hash},sort_keys=True,separators=(',',':')).encode()
            if r.previous_hash!=prev or hashlib.sha256(raw).hexdigest()!=r.record_hash:return False
            prev=r.record_hash
        return True
