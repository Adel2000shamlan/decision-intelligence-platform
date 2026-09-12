from dataclasses import dataclass
from collections import deque
from datetime import datetime, timezone
@dataclass
class Job:
    id:str; name:str; payload:dict|None=None; attempts:int=0; max_attempts:int=3; status:str='QUEUED'; last_error:str|None=None; created_at:datetime=datetime.now(timezone.utc)
class JobQueue:
    def __init__(self): self.q=deque(); self.dead=[]
    def enqueue(self,j):
        if j.max_attempts<1: raise ValueError('max_attempts must be positive')
        self.q.append(j)
    def run_once(self,handler):
        if not self.q:return None
        j=self.q.popleft()
        try: handler(j); j.status='COMPLETED'; j.last_error=None
        except Exception as e:
            j.attempts+=1; j.last_error=str(e)
            if j.attempts>=j.max_attempts:j.status='DEAD';self.dead.append(j)
            else:j.status='RETRY';self.q.append(j)
        return j
