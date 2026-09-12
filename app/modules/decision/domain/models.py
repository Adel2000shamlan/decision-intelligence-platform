from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from uuid import UUID, uuid4
from app.shared.domain.aggregate import AggregateRoot
from app.shared.domain.errors import InvalidDomainData, InvalidStateTransition, BusinessRuleViolation

class DecisionStatus(str, Enum):
    DRAFT='draft'; ANALYSIS='analysis'; READY_FOR_APPROVAL='ready_for_approval'; APPROVED='approved'; REJECTED='rejected'; CANCELLED='cancelled'; EXECUTED='executed'; CLOSED='closed'
class DecisionType(str, Enum): STRATEGIC='strategic'; OPERATIONAL='operational'; FINANCIAL='financial'; RISK='risk'; OTHER='other'
class DecisionPriority(str, Enum): LOW='low'; MEDIUM='medium'; HIGH='high'; CRITICAL='critical'

def _text(v,n,max_len=300):
    if not isinstance(v,str): raise InvalidDomainData(f'{n} must be a string')
    v=v.strip()
    if not v: raise InvalidDomainData(f'{n} is required')
    if len(v)>max_len: raise InvalidDomainData(f'{n} exceeds {max_len} characters')
    return v

@dataclass(frozen=True)
class DecisionEvent:
    event_id: UUID; occurred_at: datetime; aggregate_id: UUID; actor_id: UUID|None
@dataclass(frozen=True)
class DecisionCreated(DecisionEvent): title:str; decision_type:DecisionType; priority:DecisionPriority
@dataclass(frozen=True)
class DecisionAnalysisStarted(DecisionEvent): previous_status:DecisionStatus
@dataclass(frozen=True)
class DecisionSubmittedForApproval(DecisionEvent): previous_status:DecisionStatus
@dataclass(frozen=True)
class DecisionApproved(DecisionEvent): previous_status:DecisionStatus
@dataclass(frozen=True)
class DecisionRejected(DecisionEvent): previous_status:DecisionStatus; reason:str|None
@dataclass(frozen=True)
class DecisionCancelled(DecisionEvent): previous_status:DecisionStatus; reason:str|None
@dataclass(frozen=True)
class DecisionExecuted(DecisionEvent): previous_status:DecisionStatus
@dataclass(frozen=True)
class DecisionClosed(DecisionEvent): previous_status:DecisionStatus
@dataclass(frozen=True)
class DecisionUpdated(DecisionEvent): field_name:str; old_value:object; new_value:object

@dataclass
class Decision(AggregateRoot):
    organization_id:UUID; project_id:UUID; title:str; description:str=''; decision_type:DecisionType=DecisionType.STRATEGIC; priority:DecisionPriority=DecisionPriority.MEDIUM
    id:UUID=field(default_factory=uuid4); status:DecisionStatus=DecisionStatus.DRAFT
    created_at:datetime=field(default_factory=lambda:datetime.now(timezone.utc)); updated_at:datetime=field(default_factory=lambda:datetime.now(timezone.utc)); version:int=1
    _pending_events:list=field(default_factory=list,init=False,repr=False)
    def __post_init__(self):
        for x,n in ((self.organization_id,'organization_id'),(self.project_id,'project_id'),(self.id,'id')):
            if not isinstance(x,UUID): raise InvalidDomainData(f'{n} must be UUID')
        self.title=_text(self.title,'title');
        if not isinstance(self.description,str): raise InvalidDomainData('description must be string')
        self.description=self.description.strip()
        try:self.decision_type=DecisionType(self.decision_type)
        except (ValueError,TypeError) as e: raise InvalidDomainData('invalid decision type') from e
        try:self.priority=DecisionPriority(self.priority)
        except (ValueError,TypeError) as e: raise InvalidDomainData('invalid decision priority') from e
        try:self.status=DecisionStatus(self.status)
        except (ValueError,TypeError) as e: raise InvalidDomainData('invalid decision status') from e
        if self.version<1: raise InvalidDomainData('version must be >= 1')
    @classmethod
    def create(cls,organization_id,project_id,title,description='',decision_type=DecisionType.STRATEGIC,priority=DecisionPriority.MEDIUM,actor_id=None):
        d=cls(organization_id,project_id,title,description,decision_type,priority); d._emit(DecisionCreated(uuid4(),d.updated_at,d.id,actor_id,d.title,d.decision_type,d.priority)); return d
    def _touch(self): self.updated_at=datetime.now(timezone.utc); self.version+=1
    def _emit(self,e): self._pending_events.append(e)
    def pull_events(self): e=tuple(self._pending_events); self._pending_events.clear(); return e

    def validate_invariants(self) -> None:
        super().validate_invariants()
        from app.shared.domain.validation import DomainValidator
        DomainValidator.validate_timestamp(self.created_at, "created_at")
        DomainValidator.validate_timestamp(self.updated_at, "updated_at")
        if self.updated_at < self.created_at:
            raise InvalidDomainData("updated_at cannot precede created_at")
        pending = getattr(self, "_pending_events", [])
        DomainValidator.validate_event_sequence(pending, self.id)
        from .rules import RULES
        RULES.assert_valid(self)

    def _transition(self,target,actor,event_cls,**kwargs):
        from app.shared.domain.state_machines import DECISION_STATE_MACHINE
        DECISION_STATE_MACHINE.transition(self.status, target)
        prev=self.status; self.status=target; self._touch(); self._emit(event_cls(uuid4(),self.updated_at,self.id,actor,prev,**kwargs))
    def start_analysis(self,actor_id=None): self._transition(DecisionStatus.ANALYSIS,actor_id,DecisionAnalysisStarted)
    def submit_for_approval(self,actor_id=None): self._transition(DecisionStatus.READY_FOR_APPROVAL,actor_id,DecisionSubmittedForApproval)
    def approve(self,actor_id=None):
        if actor_id is None: raise BusinessRuleViolation('human actor approval is required')
        self._transition(DecisionStatus.APPROVED,actor_id,DecisionApproved)
    def reject(self,reason=None,actor_id=None):
        if actor_id is None: raise BusinessRuleViolation('human actor rejection is required')
        if reason is not None: reason=_text(reason,'reason',500)
        self._transition(DecisionStatus.REJECTED,actor_id,DecisionRejected,reason=reason)
    def cancel(self,reason=None,actor_id=None):
        if reason is not None: reason=_text(reason,'reason',500)
        self._transition(DecisionStatus.CANCELLED,actor_id,DecisionCancelled,reason=reason)
    def execute(self,actor_id=None): self._transition(DecisionStatus.EXECUTED,actor_id,DecisionExecuted)
    def close(self,actor_id=None): self._transition(DecisionStatus.CLOSED,actor_id,DecisionClosed)
    def update(self,field_name,value,actor_id=None):
        if self.status in (DecisionStatus.APPROVED,DecisionStatus.EXECUTED,DecisionStatus.CLOSED,DecisionStatus.CANCELLED): raise BusinessRuleViolation('decision cannot be updated in its current state')
        if field_name=='title': value=_text(value,'title')
        elif field_name=='description':
            if not isinstance(value,str): raise InvalidDomainData('description must be string')
            value=value.strip()
        elif field_name=='priority':
            try:value=DecisionPriority(value)
            except (ValueError,TypeError) as e: raise InvalidDomainData('invalid decision priority') from e
        elif field_name=='decision_type':
            try:value=DecisionType(value)
            except (ValueError,TypeError) as e: raise InvalidDomainData('invalid decision type') from e
        else: raise InvalidDomainData(f'unsupported decision field: {field_name}')
        old=getattr(self,field_name)
        if old==value:return
        setattr(self,field_name,value); self._touch(); self._emit(DecisionUpdated(uuid4(),self.updated_at,self.id,actor_id,field_name,old,value))
