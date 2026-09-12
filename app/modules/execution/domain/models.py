from dataclasses import dataclass, field
from datetime import datetime, timezone, date
from enum import Enum
from uuid import UUID, uuid4
from app.shared.domain.aggregate import AggregateRoot
from app.shared.domain.errors import InvalidDomainData, InvalidStateTransition, BusinessRuleViolation

class ExecutionStatus(str, Enum): DRAFT='draft'; PLANNED='planned'; IN_PROGRESS='in_progress'; AT_RISK='at_risk'; COMPLETED='completed'; BLOCKED='blocked'; CANCELLED='cancelled'; ARCHIVED='archived'
class HealthStatus(str, Enum): GREEN='green'; AMBER='amber'; RED='red'
class SignalType(str, Enum): POSITIVE='positive'; NEGATIVE='negative'; NEUTRAL='neutral'

@dataclass(frozen=True)
class ExecutionEvent:
    event_id: UUID; occurred_at: datetime; aggregate_id: UUID; actor_id: UUID|None
@dataclass(frozen=True)
class ExecutionCreated(ExecutionEvent): project_id: UUID; title: str
@dataclass(frozen=True)
class ExecutionProgressUpdated(ExecutionEvent): previous: float; current: float
@dataclass(frozen=True)
class ExecutionTaskUpdated(ExecutionEvent): task_id: UUID; health: HealthStatus
@dataclass(frozen=True)
class ExecutionMilestoneUpdated(ExecutionEvent): milestone_id: UUID; health: HealthStatus
@dataclass(frozen=True)
class ExecutionResourceRecorded(ExecutionEvent): consumed: float
@dataclass(frozen=True)
class ExecutionBudgetRecorded(ExecutionEvent): spent: float
@dataclass(frozen=True)
class ExecutionScheduleRecorded(ExecutionEvent): variance_days: float
@dataclass(frozen=True)
class ExecutionSignalRecorded(ExecutionEvent): signal_type: SignalType; severity: int
@dataclass(frozen=True)
class ExecutionHealthCalculated(ExecutionEvent): score: float; status: HealthStatus
@dataclass(frozen=True)
class ExecutionStatusChanged(ExecutionEvent): previous_status: ExecutionStatus; new_status: ExecutionStatus
@dataclass(frozen=True)
class ExecutionUpdated(ExecutionEvent): field_name: str; old_value: object; new_value: object

def _text(v,n,max_len=300):
    if not isinstance(v,str): raise InvalidDomainData(f'{n} must be a string')
    v=v.strip()
    if not v: raise InvalidDomainData(f'{n} is required')
    if len(v)>max_len: raise InvalidDomainData(f'{n} exceeds {max_len} characters')
    return v

def _pct(v,n):
    if not isinstance(v,(int,float)) or isinstance(v,bool) or not 0<=v<=100: raise InvalidDomainData(f'{n} must be 0..100')
    return float(v)
def _nonneg(v,n):
    if not isinstance(v,(int,float)) or isinstance(v,bool) or v<0: raise InvalidDomainData(f'{n} must be >= 0')
    return float(v)

def health_for(score):
    if score >= 80: return HealthStatus.GREEN
    if score >= 60: return HealthStatus.AMBER
    return HealthStatus.RED

@dataclass
class Task:
    title: str; weight: float=1; progress: float=0; due_date: date|None=None; id: UUID=field(default_factory=uuid4); status: str='open'; health: HealthStatus=HealthStatus.GREEN
    def __post_init__(self): self.title=_text(self.title,'task title'); self.weight=_nonneg(self.weight,'weight'); self.progress=_pct(self.progress,'progress')
    def update(self,progress,health=None): self.progress=_pct(progress,'progress'); self.health=HealthStatus(health) if health else self.health

@dataclass
class Milestone:
    title: str; target_date: date|None=None; progress: float=0; id: UUID=field(default_factory=uuid4); health: HealthStatus=HealthStatus.GREEN
    def __post_init__(self): self.title=_text(self.title,'milestone title'); self.progress=_pct(self.progress,'progress')
    def update(self,progress,health=None): self.progress=_pct(progress,'progress'); self.health=HealthStatus(health) if health else self.health

@dataclass
class Execution(AggregateRoot):
    project_id: UUID; title: str; description: str=''; planned_start: date|None=None; planned_end: date|None=None; budget: float=0; resource_plan: float=0
    id: UUID=field(default_factory=uuid4); status: ExecutionStatus=ExecutionStatus.DRAFT; progress: float=0; resources_consumed: float=0; budget_spent: float=0; schedule_variance_days: float=0; health_score: float|None=None; health_status: HealthStatus|None=None
    tasks: list[Task]=field(default_factory=list); milestones: list[Milestone]=field(default_factory=list); signals: list[tuple[SignalType,int,str]]=field(default_factory=list)
    created_at: datetime=field(default_factory=lambda: datetime.now(timezone.utc)); updated_at: datetime=field(default_factory=lambda: datetime.now(timezone.utc)); version:int=1; _pending_events:list=field(default_factory=list,init=False,repr=False)
    def __post_init__(self):
        if not isinstance(self.project_id,UUID): raise InvalidDomainData('project_id must be UUID')
        self.title=_text(self.title,'title'); self.description=self.description.strip() if isinstance(self.description,str) else (_ for _ in ()).throw(InvalidDomainData('description must be string'))
        self.budget=_nonneg(self.budget,'budget'); self.resource_plan=_nonneg(self.resource_plan,'resource_plan'); self.progress=_pct(self.progress,'progress')
        if self.planned_start and self.planned_end and self.planned_end<self.planned_start: raise InvalidDomainData('planned_end cannot precede planned_start')
    def validate_invariants(self) -> None:
        super().validate_invariants()
        from app.shared.domain.validation import DomainValidator
        DomainValidator.validate_timestamp(self.created_at, "created_at")
        DomainValidator.validate_timestamp(self.updated_at, "updated_at")
        if self.updated_at < self.created_at:
            raise InvalidDomainData("updated_at cannot precede created_at")
        from .rules import RULES
        RULES.assert_valid(self)

    @classmethod
    def create(cls,project_id,title,description='',planned_start=None,planned_end=None,budget=0,resource_plan=0,actor_id=None):
        e=cls(project_id,title,description,planned_start,planned_end,budget,resource_plan); e._emit(ExecutionCreated(uuid4(),e.updated_at,e.id,actor_id,project_id,e.title)); return e
    def _touch(self): self.updated_at=datetime.now(timezone.utc); self.version+=1
    def _emit(self,e): self._pending_events.append(e)
    def pull_events(self): out=tuple(self._pending_events); self._pending_events.clear(); return out
    def _transition(self,target,actor=None):
        from app.shared.domain.state_machines import EXECUTION_STATE_MACHINE
        EXECUTION_STATE_MACHINE.transition(self.status, target)
        prev=self.status; self.status=target; self._touch(); self._emit(ExecutionStatusChanged(uuid4(),self.updated_at,self.id,actor,prev,target))
    def plan(self,actor_id=None): self._transition(ExecutionStatus.PLANNED,actor_id)
    def start(self,actor_id=None):
        if not self.tasks and not self.milestones: pass
        self._transition(ExecutionStatus.IN_PROGRESS,actor_id)
    def mark_at_risk(self,actor_id=None): self._transition(ExecutionStatus.AT_RISK,actor_id)
    def block(self,actor_id=None): self._transition(ExecutionStatus.BLOCKED,actor_id)
    def complete(self,actor_id=None):
        if self.progress < 100: raise BusinessRuleViolation('execution cannot be completed before progress reaches 100')
        self._transition(ExecutionStatus.COMPLETED,actor_id)
    def cancel(self,actor_id=None): self._transition(ExecutionStatus.CANCELLED,actor_id)
    def archive(self,actor_id=None): self._transition(ExecutionStatus.ARCHIVED,actor_id)
    def update_progress(self,progress,actor_id=None):
        p=_pct(progress,'progress'); old=self.progress; self.progress=p; self._touch(); self._emit(ExecutionProgressUpdated(uuid4(),self.updated_at,self.id,actor_id,old,p))
    def add_task(self,title,weight=1,due_date=None):
        t=Task(title,weight,0,due_date); self.tasks.append(t); self._touch(); return t
    def update_task(self,task_id,progress,health=None,actor_id=None):
        t=next((x for x in self.tasks if x.id==task_id),None)
        if not t: raise BusinessRuleViolation('task not found')
        t.update(progress,health); self._touch(); self._emit(ExecutionTaskUpdated(uuid4(),self.updated_at,self.id,actor_id,t.id,t.health)); self.recalculate_progress(actor_id)
    def add_milestone(self,title,target_date=None):
        m=Milestone(title,target_date); self.milestones.append(m); self._touch(); return m
    def update_milestone(self,milestone_id,progress,health=None,actor_id=None):
        m=next((x for x in self.milestones if x.id==milestone_id),None)
        if not m: raise BusinessRuleViolation('milestone not found')
        m.update(progress,health); self._touch(); self._emit(ExecutionMilestoneUpdated(uuid4(),self.updated_at,self.id,actor_id,m.id,m.health)); self.recalculate_progress(actor_id)
    def recalculate_progress(self,actor_id=None):
        if self.tasks:
            total=sum(t.weight for t in self.tasks)
            self.update_progress(sum(t.progress*t.weight for t in self.tasks)/total if total else 0,actor_id)
        elif self.milestones: self.update_progress(sum(m.progress for m in self.milestones)/len(self.milestones),actor_id)
    def record_resource_consumption(self,amount,actor_id=None):
        a=_nonneg(amount,'amount'); self.resources_consumed+=a; self._touch(); self._emit(ExecutionResourceRecorded(uuid4(),self.updated_at,self.id,actor_id,self.resources_consumed))
    def record_budget_spend(self,amount,actor_id=None):
        a=_nonneg(amount,'amount'); self.budget_spent+=a; self._touch(); self._emit(ExecutionBudgetRecorded(uuid4(),self.updated_at,self.id,actor_id,self.budget_spent))
    def record_schedule_variance(self,days,actor_id=None):
        if not isinstance(days,(int,float)) or isinstance(days,bool): raise InvalidDomainData('variance days must be numeric')
        self.schedule_variance_days=float(days); self._touch(); self._emit(ExecutionScheduleRecorded(uuid4(),self.updated_at,self.id,actor_id,self.schedule_variance_days))
    def record_signal(self,signal_type,severity,message='',actor_id=None):
        st=SignalType(signal_type); s=int(severity)
        if not 1<=s<=5: raise InvalidDomainData('severity must be 1..5')
        self.signals.append((st,s,message.strip())); self._touch(); self._emit(ExecutionSignalRecorded(uuid4(),self.updated_at,self.id,actor_id,st,s))
    def calculate_health(self,actor_id=None):
        budget_score=100 if self.budget==0 else max(0,100-(self.budget_spent/self.budget)*100)
        resource_score=100 if self.resource_plan==0 else max(0,100-(self.resources_consumed/self.resource_plan)*100)
        schedule_score=max(0,100-abs(self.schedule_variance_days)*5)
        task_score=100 if not self.tasks else sum((100 if t.health is HealthStatus.GREEN else 70 if t.health is HealthStatus.AMBER else 30)*t.weight for t in self.tasks)/sum(t.weight for t in self.tasks)
        signal_penalty=sum(s*4 for _,s,_ in self.signals[-10:]); score=max(0,min(100,0.35*self.progress+0.2*budget_score+0.15*resource_score+0.15*schedule_score+0.15*task_score-signal_penalty))
        self.health_score=round(score,2); self.health_status=health_for(self.health_score); self._touch(); self._emit(ExecutionHealthCalculated(uuid4(),self.updated_at,self.id,actor_id,self.health_score,self.health_status)); return self.health_score
    def rename(self,new_title,actor_id=None):
        v=_text(new_title,'title')
        if v==self.title:return
        old=self.title; self.title=v; self._touch(); self._emit(ExecutionUpdated(uuid4(),self.updated_at,self.id,actor_id,'title',old,v))
