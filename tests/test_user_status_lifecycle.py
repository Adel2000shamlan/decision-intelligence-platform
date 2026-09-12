from uuid import uuid4
import pytest
from app.modules.identity import InMemoryUserRepository
from app.modules.identity.domain.models import User,UserStatus,UserSuspended,UserReactivated,UserArchived
from app.modules.identity.domain.services import UserLifecycleService
from app.shared.domain.aggregate import AggregateBoundary
from app.shared.domain.errors import BusinessRuleViolation,InvalidStateTransition

def make(): return User.create('user@example.com','User')

def test_initial_state_is_active_and_create_version_is_one():
    u=make(); assert u.status is UserStatus.ACTIVE and u.version==1

def test_active_to_suspended_records_event_and_increments_version():
    u=make(); u.pull_events(); actor=uuid4(); u.suspend(actor,'security review')
    assert u.status is UserStatus.SUSPENDED and u.version==2
    ev=u.pull_events()[0]; assert isinstance(ev,UserSuspended) and ev.actor_id==actor and ev.reason=='security review'

def test_suspended_to_active_records_reactivation():
    u=make(); u.pull_events(); u.suspend(); u.pull_events(); u.reactivate()
    assert u.status is UserStatus.ACTIVE and u.version==3
    assert isinstance(u.pull_events()[0],UserReactivated)

def test_active_to_archived_is_terminal():
    u=make(); u.pull_events(); u.archive(reason='account closure'); u.pull_events()
    assert u.status is UserStatus.ARCHIVED
    with pytest.raises(InvalidStateTransition): u.reactivate()
    with pytest.raises(BusinessRuleViolation): u.rename('New')

def test_suspended_to_archived_is_allowed():
    u=make(); u.suspend(); u.pull_events(); u.archive(); assert u.status is UserStatus.ARCHIVED

def test_invalid_lifecycle_transition_does_not_mutate():
    u=make(); before=(u.status,u.version); u.pull_events()
    with pytest.raises(InvalidStateTransition): u.reactivate()
    assert (u.status,u.version)==before and u.pull_events()==()

def test_archive_is_idempotency_guarded_by_state_machine():
    u=make(); u.pull_events(); u.archive(); u.pull_events(); before=u.version
    with pytest.raises(InvalidStateTransition): u.archive()
    assert u.version==before

def test_service_expected_version_prevents_stale_lifecycle_change():
    repo=InMemoryUserRepository(); service=UserLifecycleService(); u=service.create(repo,'user@example.com','User').entity; u.pull_events()
    service.suspend(repo,u.id,expected_version=1)
    with pytest.raises(BusinessRuleViolation): service.reactivate(repo,u.id,expected_version=1)
    assert repo.get_by_id(u.id).status is UserStatus.SUSPENDED

def test_service_not_found():
    repo=InMemoryUserRepository()
    with pytest.raises(Exception): UserLifecycleService().suspend(repo,uuid4())

def test_aggregate_boundary_preserves_events():
    u=make(); AggregateBoundary.validate(u); assert len(u.pull_events())==1

def test_rename_is_blocked_only_when_archived():
    u=make(); u.pull_events(); u.rename('New Name'); assert u.name=='New Name'; assert u.version==2

def test_lifecycle_invariants():
    u=make(); AggregateBoundary.validate(u); u.suspend(); AggregateBoundary.validate(u); u.pull_events(); u.archive(); AggregateBoundary.validate(u)
