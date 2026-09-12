from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from uuid import UUID, uuid4
from app.shared.domain.aggregate import AggregateRoot
from app.shared.domain.errors import InvalidDomainData, InvalidStateTransition, BusinessRuleViolation

class RiskStatus(str, Enum):
    DRAFT='draft'; IDENTIFIED='identified'; ASSESSED='assessed'; MITIGATING='mitigating'; MONITORED='monitored'; CLOSED='closed'; ACCEPTED='accepted'; ARCHIVED='archived'
class RiskSource(str, Enum): HUMAN='human'; AI='ai'; SYSTEM='system'
class RiskLevel(str, Enum): LOW='low'; MEDIUM='medium'; HIGH='high'; CRITICAL='critical'

@dataclass(frozen=True)
class RiskEvent:
    event_id: UUID; occurred_at: datetime; aggregate_id: UUID; actor_id: UUID|None
@dataclass(frozen=True)
class RiskCreated(RiskEvent): title: str; source: RiskSource
@dataclass(frozen=True)
class RiskIdentified(RiskEvent): previous_status: RiskStatus
@dataclass(frozen=True)
class RiskAssessed(RiskEvent): probability: int; impact: int; score: int; level: RiskLevel
@dataclass(frozen=True)
class RiskMitigationStarted(RiskEvent): previous_status: RiskStatus
@dataclass(frozen=True)
class RiskMonitored(RiskEvent): residual_score: int; residual_level: RiskLevel
@dataclass(frozen=True)
class RiskAccepted(RiskEvent): previous_status: RiskStatus
@dataclass(frozen=True)
class RiskClosed(RiskEvent): previous_status: RiskStatus
@dataclass(frozen=True)
class RiskArchived(RiskEvent): previous_status: RiskStatus
@dataclass(frozen=True)
class RiskUpdated(RiskEvent): field_name: str; old_value: object; new_value: object

def _text(v, name, max_len=300):
    if not isinstance(v,str): raise InvalidDomainData(f'{name} must be a string')
    v=v.strip()
    if not v: raise InvalidDomainData(f'{name} is required')
    if len(v)>max_len: raise InvalidDomainData(f'{name} exceeds {max_len} characters')
    return v

def _score(probability, impact): return probability*impact

def level_for(score):
    if score <= 4: return RiskLevel.LOW
    if score <= 9: return RiskLevel.MEDIUM
    if score <= 16: return RiskLevel.HIGH
    return RiskLevel.CRITICAL

@dataclass
class Risk(AggregateRoot):
    project_id: UUID
    title: str
    description: str=''
    decision_id: UUID|None=None
    source: RiskSource=RiskSource.HUMAN
    id: UUID=field(default_factory=uuid4)
    status: RiskStatus=RiskStatus.DRAFT
    probability: int|None=None
    impact: int|None=None
    score: int|None=None
    level: RiskLevel|None=None
    residual_probability: int|None=None
    residual_impact: int|None=None
    residual_score: int|None=None
    residual_level: RiskLevel|None=None
    created_at: datetime=field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime=field(default_factory=lambda: datetime.now(timezone.utc))
    version: int=1
    _pending_events: list[object]=field(default_factory=list, init=False, repr=False)
    def __post_init__(self):
        if not isinstance(self.project_id,UUID): raise InvalidDomainData('project_id must be UUID')
        if self.decision_id is not None and not isinstance(self.decision_id,UUID): raise InvalidDomainData('decision_id must be UUID')
        self.title=_text(self.title,'title')
        if not isinstance(self.description,str): raise InvalidDomainData('description must be string')
        self.description=self.description.strip()
        if not isinstance(self.source,RiskSource):
            try:self.source=RiskSource(self.source)
            except (ValueError,TypeError) as e: raise InvalidDomainData('invalid risk source') from e
        if not isinstance(self.status,RiskStatus):
            try:self.status=RiskStatus(self.status)
            except (ValueError,TypeError) as e: raise InvalidDomainData('invalid risk status') from e
        if self.version<1: raise InvalidDomainData('version must be >= 1')
        for n,v in [('probability',self.probability),('impact',self.impact),('residual_probability',self.residual_probability),('residual_impact',self.residual_impact)]:
            if v is not None: self._validate_rating(v,n)
    @staticmethod
    def _validate_rating(v,n):
        if not isinstance(v,int) or isinstance(v,bool) or not 1<=v<=5: raise InvalidDomainData(f'{n} must be integer 1..5')
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
    def create(cls, project_id, title, description='', decision_id=None, source=RiskSource.HUMAN, actor_id=None):
        r=cls(project_id,title,description,decision_id,source); r._emit(RiskCreated(uuid4(),r.updated_at,r.id,actor_id,r.title,r.source)); return r
    def _touch(self): self.updated_at=datetime.now(timezone.utc); self.version+=1
    def _emit(self,e): self._pending_events.append(e)
    def pull_events(self): e=tuple(self._pending_events); self._pending_events.clear(); return e
    def _transition(self,target,actor,event_type):
        from app.shared.domain.state_machines import RISK_STATE_MACHINE
        RISK_STATE_MACHINE.transition(self.status, target)
        prev=self.status; self.status=target; self._touch(); self._emit(event_type(uuid4(),self.updated_at,self.id,actor,prev) if event_type in (RiskIdentified,RiskMitigationStarted,RiskAccepted,RiskClosed,RiskArchived) else event_type(uuid4(),self.updated_at,self.id,actor))
    def identify(self,actor_id=None): self._transition(RiskStatus.IDENTIFIED,actor_id,RiskIdentified)
    def assess(self,probability,impact,actor_id=None):
        self._validate_rating(probability,'probability'); self._validate_rating(impact,'impact')
        if self.status is not RiskStatus.IDENTIFIED: raise InvalidStateTransition(f'risk: {self.status.value}->assessed not allowed')
        self.probability=probability; self.impact=impact; self.score=_score(probability,impact); self.level=level_for(self.score); self._touch(); self.status=RiskStatus.ASSESSED; self._emit(RiskAssessed(uuid4(),self.updated_at,self.id,actor_id,probability,impact,self.score,self.level))
    def start_mitigation(self,actor_id=None): self._transition(RiskStatus.MITIGATING,actor_id,RiskMitigationStarted)
    def monitor(self,residual_probability,residual_impact,actor_id=None):
        self._validate_rating(residual_probability,'residual_probability'); self._validate_rating(residual_impact,'residual_impact')
        if self.status not in (RiskStatus.MITIGATING,RiskStatus.MONITORED,RiskStatus.ASSESSED): raise InvalidStateTransition(f'risk: {self.status.value}->monitored not allowed')
        self.residual_probability=residual_probability; self.residual_impact=residual_impact; self.residual_score=_score(residual_probability,residual_impact); self.residual_level=level_for(self.residual_score)
        if self.status is not RiskStatus.MONITORED: self.status=RiskStatus.MONITORED
        self._touch(); self._emit(RiskMonitored(uuid4(),self.updated_at,self.id,actor_id,self.residual_score,self.residual_level))
    def accept(self,actor_id=None): self._transition(RiskStatus.ACCEPTED,actor_id,RiskAccepted)
    def close(self,actor_id=None): self._transition(RiskStatus.CLOSED,actor_id,RiskClosed)
    def archive(self,actor_id=None): self._transition(RiskStatus.ARCHIVED,actor_id,RiskArchived)
    def rename(self,new_title,actor_id=None):
        v=_text(new_title,'title')
        if v==self.title:return
        old=self.title; self.title=v; self._touch(); self._emit(RiskUpdated(uuid4(),self.updated_at,self.id,actor_id,'title',old,v))
    def ensure_assessed(self):
        if self.score is None or self.level is None: raise BusinessRuleViolation('risk must be assessed before this operation')
