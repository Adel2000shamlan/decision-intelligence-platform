from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from uuid import UUID, uuid4
from app.shared.domain.aggregate import AggregateRoot
from app.shared.domain.errors import InvalidDomainData, BusinessRuleViolation
from app.shared.domain.value_objects import Description, EmailAddress, Name

class UserStatus(str, Enum):
    ACTIVE='active'; SUSPENDED='suspended'; ARCHIVED='archived'

@dataclass(frozen=True)
class UserCreated:
    event_id: UUID; occurred_at: datetime; aggregate_id: UUID; actor_id: UUID|None=None; email: str=''; display_name: str=''
@dataclass(frozen=True)
class UserSuspended:
    event_id: UUID; occurred_at: datetime; aggregate_id: UUID; actor_id: UUID|None=None; reason: str=''
@dataclass(frozen=True)
class UserReactivated:
    event_id: UUID; occurred_at: datetime; aggregate_id: UUID; actor_id: UUID|None=None
@dataclass(frozen=True)
class UserArchived:
    event_id: UUID; occurred_at: datetime; aggregate_id: UUID; actor_id: UUID|None=None; reason: str=''
@dataclass(frozen=True)
class UserRenamed:
    event_id: UUID; occurred_at: datetime; aggregate_id: UUID; actor_id: UUID|None=None; old_name: str=''; new_name: str=''

@dataclass
class User(AggregateRoot):
    email: EmailAddress|str
    display_name: Name|str
    description: Description|str=''
    id: UUID=field(default_factory=uuid4)
    status: UserStatus=UserStatus.ACTIVE
    created_at: datetime=field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime=field(default_factory=lambda: datetime.now(timezone.utc))
    version: int=1
    _pending_events: list[object]=field(default_factory=list, init=False, repr=False)

    def __post_init__(self):
        self.email=self.email if isinstance(self.email,EmailAddress) else EmailAddress(self.email)
        self.display_name=self.display_name if isinstance(self.display_name,Name) else Name(self.display_name)
        self.description=self.description if isinstance(self.description,Description) else Description(self.description)
        if not isinstance(self.status,UserStatus):
            try:self.status=UserStatus(self.status)
            except (ValueError,TypeError) as exc: raise InvalidDomainData('invalid user status') from exc
        if not isinstance(self.id,UUID): raise InvalidDomainData('user id must be UUID')
        if isinstance(self.version,bool) or not isinstance(self.version,int) or self.version<1: raise InvalidDomainData('version must be integer >= 1')
        if not isinstance(self.created_at,datetime) or not isinstance(self.updated_at,datetime): raise InvalidDomainData('user timestamps must be datetime')
        if self.created_at.tzinfo is None or self.updated_at.tzinfo is None: raise InvalidDomainData('user timestamps must be timezone-aware')
        if self.updated_at<self.created_at: raise InvalidDomainData('updated_at cannot precede created_at')

    @classmethod
    def create(cls,email,display_name,description='',actor_id=None):
        user=cls(email,display_name,description)
        user._record(UserCreated(uuid4(),user.updated_at,user.id,actor_id,str(user.email),user.name), increment=False)
        return user
    @property
    def email_address(self): return self.email.value
    @property
    def name(self): return self.display_name.value
    @property
    def is_active(self): return self.status is UserStatus.ACTIVE
    @property
    def is_suspended(self): return self.status is UserStatus.SUSPENDED
    @property
    def is_archived(self): return self.status is UserStatus.ARCHIVED

    def _record(self,event,increment=True):
        self._pending_events.append(event)
        if increment: self.version += 1
        self.updated_at = datetime.now(timezone.utc)
    def _transition(self,target,actor_id=None,reason=''):
        from app.shared.domain.state_machines import USER_STATE_MACHINE
        current=self.status; self.status=USER_STATE_MACHINE.transition(current,target)
        if self.status is not current: self._record_event_for_transition(current,self.status,actor_id,reason)
    def _record_event_for_transition(self,source,target,actor_id,reason):
        now=datetime.now(timezone.utc)
        if target is UserStatus.SUSPENDED: ev=UserSuspended(uuid4(),now,self.id,actor_id,reason)
        elif target is UserStatus.ACTIVE: ev=UserReactivated(uuid4(),now,self.id,actor_id)
        elif target is UserStatus.ARCHIVED: ev=UserArchived(uuid4(),now,self.id,actor_id,reason)
        else: raise InvalidDomainData('unsupported user lifecycle event')
        self._record(ev)

    def suspend(self,actor_id=None,reason=''):
        if self.status is UserStatus.ARCHIVED: raise BusinessRuleViolation('archived user cannot be suspended')
        self._transition(UserStatus.SUSPENDED,actor_id,reason)
    def reactivate(self,actor_id=None):
        self._transition(UserStatus.ACTIVE,actor_id)
    def archive(self,actor_id=None,reason=''):
        self._transition(UserStatus.ARCHIVED,actor_id,reason)
    def rename(self,new_name,actor_id=None):
        if self.status is UserStatus.ARCHIVED: raise BusinessRuleViolation('archived user cannot be renamed')
        new=Name(new_name)
        if new.value==self.name: return
        old=self.name; self.display_name=new
        self._record(UserRenamed(uuid4(),datetime.now(timezone.utc),self.id,actor_id,old,new.value))

    def validate_invariants(self):
        super().validate_invariants()
        from app.shared.domain.validation import DomainValidator
        from .rules import USER_RULE_SET
        from .security import CredentialBoundaryContract
        DomainValidator.validate_timestamp(self.created_at,'created_at'); DomainValidator.validate_timestamp(self.updated_at,'updated_at')
        if self.updated_at<self.created_at: raise InvalidDomainData('updated_at cannot precede created_at')
        if not isinstance(self.email,EmailAddress): raise InvalidDomainData('email must be EmailAddress')
        if not isinstance(self.display_name,Name): raise InvalidDomainData('display_name must be Name')
        if not isinstance(self.description,Description): raise InvalidDomainData('description must be Description')
        if not isinstance(self.status,UserStatus): raise InvalidDomainData('invalid user status')
        DomainValidator.validate_event_sequence(self._pending_events,self.id)
        CredentialBoundaryContract.assert_user_boundary(self)
        for event in self._pending_events:
            CredentialBoundaryContract.assert_event_safe(event)
        USER_RULE_SET.assert_valid(self, None)
    def pull_events(self):
        events=tuple(self._pending_events); self._pending_events.clear(); return events
