from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from uuid import UUID, uuid4
from app.shared.domain.aggregate import AggregateRoot
from app.shared.domain.errors import InvalidDomainData, InvalidStateTransition, BusinessRuleViolation

class OptionStatus(str, Enum):
    DRAFT='draft'; UNDER_EVALUATION='under_evaluation'; ELIGIBLE='eligible'; SELECTED='selected'; REJECTED='rejected'; WITHDRAWN='withdrawn'; ARCHIVED='archived'
class OptionType(str, Enum): ORIGINAL='original'; ALTERNATIVE='alternative'; CUSTOM='custom'
class OptionSource(str, Enum): HUMAN='human'; AI='ai'; SYSTEM='system'

@dataclass(frozen=True)
class OptionEvent:
    event_id: UUID; occurred_at: datetime; aggregate_id: UUID; actor_id: UUID|None
@dataclass(frozen=True)
class OptionCreated(OptionEvent): title: str; option_type: OptionType; source: OptionSource
@dataclass(frozen=True)
class OptionUpdated(OptionEvent): field_name: str; old_value: object; new_value: object
@dataclass(frozen=True)
class OptionEvaluationStarted(OptionEvent): previous_status: OptionStatus
@dataclass(frozen=True)
class OptionMarkedEligible(OptionEvent): previous_status: OptionStatus
@dataclass(frozen=True)
class OptionSelected(OptionEvent): previous_status: OptionStatus
@dataclass(frozen=True)
class OptionRejected(OptionEvent): previous_status: OptionStatus
@dataclass(frozen=True)
class OptionWithdrawn(OptionEvent): previous_status: OptionStatus
@dataclass(frozen=True)
class OptionArchived(OptionEvent): previous_status: OptionStatus

def _text(v,name,max_len=300):
    if not isinstance(v,str): raise InvalidDomainData(f'{name} must be a string')
    v=v.strip()
    if not v: raise InvalidDomainData(f'{name} is required')
    if len(v)>max_len: raise InvalidDomainData(f'{name} exceeds {max_len} characters')
    return v

def _enum(v,cls,name):
    if isinstance(v,cls): return v
    try: return cls(v)
    except (ValueError,TypeError) as e: raise InvalidDomainData(f'invalid {name}') from e

@dataclass
class Option(AggregateRoot):
    decision_id: UUID
    title: str
    description: str=''
    option_type: OptionType=OptionType.ORIGINAL
    source: OptionSource=OptionSource.HUMAN
    rank: int|None=None
    id: UUID=field(default_factory=uuid4)
    status: OptionStatus=OptionStatus.DRAFT
    created_at: datetime=field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime=field(default_factory=lambda: datetime.now(timezone.utc))
    version: int=1
    _pending_events: list[object]=field(default_factory=list, init=False, repr=False)
    def __post_init__(self):
        if not isinstance(self.decision_id,UUID): raise InvalidDomainData('decision_id must be UUID')
        self.title=_text(self.title,'title')
        if not isinstance(self.description,str): raise InvalidDomainData('description must be string')
        self.description=self.description.strip()
        self.option_type=_enum(self.option_type,OptionType,'option type')
        self.source=_enum(self.source,OptionSource,'option source')
        self.status=_enum(self.status,OptionStatus,'option status')
        if self.rank is not None and (not isinstance(self.rank,int) or isinstance(self.rank,bool) or self.rank<1): raise InvalidDomainData('rank must be a positive integer')
        if self.version<1: raise InvalidDomainData('version must be >= 1')
        if self.source is OptionSource.AI and self.option_type is not OptionType.ALTERNATIVE: raise BusinessRuleViolation('AI-generated options must be marked as alternative')
    @classmethod
    def create(cls,decision_id,title,description='',option_type=OptionType.ORIGINAL,source=OptionSource.HUMAN,rank=None,actor_id=None):
        o=cls(decision_id,title,description,option_type,source,rank)
        o._emit(OptionCreated(uuid4(),o.updated_at,o.id,actor_id,o.title,o.option_type,o.source)); return o
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

    def _transition(self,target,actor,event_type):
        from app.shared.domain.state_machines import OPTION_STATE_MACHINE
        OPTION_STATE_MACHINE.transition(self.status, target)
        prev=self.status; self.status=target; self._touch(); self._emit(event_type(uuid4(),self.updated_at,self.id,actor,prev))
    def start_evaluation(self,actor_id=None): self._transition(OptionStatus.UNDER_EVALUATION,actor_id,OptionEvaluationStarted)
    def mark_eligible(self,actor_id=None): self._transition(OptionStatus.ELIGIBLE,actor_id,OptionMarkedEligible)
    def select(self,actor_id=None):
        if self.option_type is OptionType.ORIGINAL and self.status is OptionStatus.ELIGIBLE: pass
        self._transition(OptionStatus.SELECTED,actor_id,OptionSelected)
    def reject(self,actor_id=None): self._transition(OptionStatus.REJECTED,actor_id,OptionRejected)
    def withdraw(self,actor_id=None): self._transition(OptionStatus.WITHDRAWN,actor_id,OptionWithdrawn)
    def archive(self,actor_id=None): self._transition(OptionStatus.ARCHIVED,actor_id,OptionArchived)
    def update(self,actor_id=None,**changes):
        if self.status in (OptionStatus.SELECTED,OptionStatus.WITHDRAWN,OptionStatus.ARCHIVED): raise BusinessRuleViolation('terminal option state cannot be updated')
        allowed={'title','description','option_type','source','rank'}
        for name,value in changes.items():
            if name not in allowed: raise InvalidDomainData(f'unsupported option field: {name}')
            if name=='title': value=_text(value,'title')
            elif name=='description':
                if not isinstance(value,str): raise InvalidDomainData('description must be string')
                value=value.strip()
            elif name=='option_type': value=_enum(value,OptionType,'option type')
            elif name=='source': value=_enum(value,OptionSource,'option source')
            elif name=='rank':
                if value is not None and (not isinstance(value,int) or isinstance(value,bool) or value<1): raise InvalidDomainData('rank must be a positive integer')
            if name=='source' and value is OptionSource.AI and changes.get('option_type',self.option_type) is not OptionType.ALTERNATIVE: raise BusinessRuleViolation('AI-generated options must be marked as alternative')
            if name=='option_type' and self.source is OptionSource.AI and value is not OptionType.ALTERNATIVE: raise BusinessRuleViolation('AI-generated options must be marked as alternative')
            old=getattr(self,name)
            if old==value: continue
            setattr(self,name,value); self._touch(); self._emit(OptionUpdated(uuid4(),self.updated_at,self.id,actor_id,name,old,value))
