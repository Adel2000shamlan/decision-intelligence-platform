from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from uuid import UUID, uuid4
from app.shared.domain.aggregate import AggregateRoot
from app.shared.domain.errors import InvalidDomainData, InvalidStateTransition, BusinessRuleViolation

class ScenarioStatus(str, Enum):
    DRAFT='draft'; UNDER_ANALYSIS='under_analysis'; EVALUATED='evaluated'; APPROVED='approved'; REJECTED='rejected'; ARCHIVED='archived'
class ScenarioType(str, Enum):
    BEST_CASE='best_case'; BASE_CASE='base_case'; DOWNSIDE_CASE='downside_case'; CUSTOM='custom'
class ScenarioSource(str, Enum):
    HUMAN='human'; AI='ai'; SYSTEM='system'

@dataclass(frozen=True)
class ScenarioEvent:
    event_id: UUID; occurred_at: datetime; aggregate_id: UUID; actor_id: UUID|None
@dataclass(frozen=True)
class ScenarioCreated(ScenarioEvent):
    name: str; scenario_type: ScenarioType; source: ScenarioSource
@dataclass(frozen=True)
class ScenarioUpdated(ScenarioEvent):
    field_name: str; old_value: object; new_value: object
@dataclass(frozen=True)
class ScenarioAnalysisStarted(ScenarioEvent): previous_status: ScenarioStatus
@dataclass(frozen=True)
class ScenarioEvaluated(ScenarioEvent): previous_status: ScenarioStatus
@dataclass(frozen=True)
class ScenarioApproved(ScenarioEvent): previous_status: ScenarioStatus
@dataclass(frozen=True)
class ScenarioRejected(ScenarioEvent): previous_status: ScenarioStatus
@dataclass(frozen=True)
class ScenarioArchived(ScenarioEvent): previous_status: ScenarioStatus

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

def _percentage(v,name):
    if not isinstance(v,(int,float)) or isinstance(v,bool) or not 0 <= v <= 100:
        raise InvalidDomainData(f'{name} must be between 0 and 100')
    return v

@dataclass
class Scenario(AggregateRoot):
    decision_id: UUID
    option_id: UUID
    name: str
    description: str=''
    scenario_type: ScenarioType=ScenarioType.CUSTOM
    source: ScenarioSource=ScenarioSource.HUMAN
    probability: float|None=None
    confidence: float|None=None
    id: UUID=field(default_factory=uuid4)
    status: ScenarioStatus=ScenarioStatus.DRAFT
    created_at: datetime=field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime=field(default_factory=lambda: datetime.now(timezone.utc))
    version: int=1
    _pending_events: list[object]=field(default_factory=list, init=False, repr=False)

    def __post_init__(self):
        if not isinstance(self.decision_id,UUID): raise InvalidDomainData('decision_id must be UUID')
        if not isinstance(self.option_id,UUID): raise InvalidDomainData('option_id must be UUID')
        self.name=_text(self.name,'name')
        if not isinstance(self.description,str): raise InvalidDomainData('description must be string')
        self.description=self.description.strip()
        self.scenario_type=_enum(self.scenario_type,ScenarioType,'scenario type')
        self.source=_enum(self.source,ScenarioSource,'scenario source')
        self.status=_enum(self.status,ScenarioStatus,'scenario status')
        if self.probability is not None: self.probability=_percentage(self.probability,'probability')
        if self.confidence is not None: self.confidence=_percentage(self.confidence,'confidence')
        if self.version < 1: raise InvalidDomainData('version must be >= 1')

    @classmethod
    def create(cls, decision_id, option_id, name, description='', scenario_type=ScenarioType.CUSTOM,
               source=ScenarioSource.HUMAN, probability=None, confidence=None, actor_id=None):
        s=cls(decision_id,option_id,name,description,scenario_type,source,probability,confidence)
        s._emit(ScenarioCreated(uuid4(),s.updated_at,s.id,actor_id,s.name,s.scenario_type,s.source)); return s

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
        from app.shared.domain.state_machines import SCENARIO_STATE_MACHINE
        SCENARIO_STATE_MACHINE.transition(self.status, target)
        prev=self.status; self.status=target; self._touch(); self._emit(event_type(uuid4(),self.updated_at,self.id,actor,prev))

    def start_analysis(self,actor_id=None): self._transition(ScenarioStatus.UNDER_ANALYSIS,actor_id,ScenarioAnalysisStarted)
    def evaluate(self,actor_id=None): self._transition(ScenarioStatus.EVALUATED,actor_id,ScenarioEvaluated)
    def approve(self,actor_id=None):
        if actor_id is None: raise BusinessRuleViolation('scenario approval requires an explicit human actor_id')
        self._transition(ScenarioStatus.APPROVED,actor_id,ScenarioApproved)
    def reject(self,actor_id=None): self._transition(ScenarioStatus.REJECTED,actor_id,ScenarioRejected)
    def archive(self,actor_id=None): self._transition(ScenarioStatus.ARCHIVED,actor_id,ScenarioArchived)

    def update(self,actor_id=None,**changes):
        if self.status in (ScenarioStatus.APPROVED,ScenarioStatus.ARCHIVED): raise BusinessRuleViolation('approved or archived scenario cannot be updated')
        allowed={'name','description','scenario_type','source','probability','confidence'}
        for name,value in changes.items():
            if name not in allowed: raise InvalidDomainData(f'unsupported scenario field: {name}')
            if name=='name': value=_text(value,'name')
            elif name=='description':
                if not isinstance(value,str): raise InvalidDomainData('description must be string')
                value=value.strip()
            elif name=='scenario_type': value=_enum(value,ScenarioType,'scenario type')
            elif name=='source': value=_enum(value,ScenarioSource,'scenario source')
            elif name in ('probability','confidence'):
                if value is not None: value=_percentage(value,name)
            old=getattr(self,name)
            if old==value: continue
            setattr(self,name,value); self._touch(); self._emit(ScenarioUpdated(uuid4(),self.updated_at,self.id,actor_id,name,old,value))
