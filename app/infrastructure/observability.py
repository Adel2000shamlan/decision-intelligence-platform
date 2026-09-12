from dataclasses import dataclass
from datetime import datetime, timezone
import logging, time, uuid
@dataclass(frozen=True)
class TraceSpan:
    trace_id:str; name:str; duration_ms:float; success:bool
class Metrics:
    def __init__(self): self.counters={}; self.timings={}
    def inc(self,name,value=1): self.counters[name]=self.counters.get(name,0)+value
    def observe(self,name,value): self.timings.setdefault(name,[]).append(float(value))
class Observability:
    def __init__(self,metrics=None,logger=None): self.metrics=metrics or Metrics(); self.logger=logger or logging.getLogger('decision_intelligence')
    def operation(self,name,fn,*args,**kwargs):
        trace_id=uuid.uuid4().hex; start=time.perf_counter()
        try:
            out=fn(*args,**kwargs); self.metrics.inc(f'{name}.success'); return out
        except Exception:
            self.metrics.inc(f'{name}.error'); raise
        finally:
            self.metrics.observe(f'{name}.duration_ms',(time.perf_counter()-start)*1000); self.logger.info('operation=%s trace_id=%s',name,trace_id)
