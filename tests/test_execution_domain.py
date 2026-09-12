from datetime import date
from uuid import uuid4
import pytest
from app.modules.execution.domain.models import *
from app.modules.execution.in_memory import InMemoryExecutionRepository
from app.modules.execution.domain.services import ExecutionPolicyService
from app.shared.domain.errors import InvalidDomainData, InvalidStateTransition, BusinessRuleViolation

P=uuid4()
def ex(): return Execution.create(P,'Launch Program',budget=1000,resource_plan=100)

def test_create_defaults_and_event():
 e=ex(); assert e.status is ExecutionStatus.DRAFT; assert e.progress==0; assert isinstance(e.pull_events()[0],ExecutionCreated)
def test_validation():
 with pytest.raises(InvalidDomainData): Execution.create(P,'')
 with pytest.raises(InvalidDomainData): Execution.create(P,'x',budget=-1)
 with pytest.raises(InvalidDomainData): Execution.create(P,'x',planned_start=date(2026,2,1),planned_end=date(2026,1,1))
def test_lifecycle():
 e=ex(); e.plan(); e.start(); e.mark_at_risk(); e.start(); e.update_progress(100); e.complete(); e.archive(); assert e.status is ExecutionStatus.ARCHIVED
def test_invalid_transition():
 e=ex();
 with pytest.raises(BusinessRuleViolation): e.complete()
 e.update_progress(100)
 with pytest.raises(InvalidStateTransition): e.complete()
def test_block_and_resume():
 e=ex(); e.plan(); e.start(); e.block(); assert e.status is ExecutionStatus.BLOCKED; e.start(); assert e.status is ExecutionStatus.IN_PROGRESS
def test_cancel_archive():
 e=ex(); e.cancel(); e.archive(); assert e.status is ExecutionStatus.ARCHIVED
def test_terminal_mutation_policy():
 e=ex(); e.plan(); e.start(); e.update_progress(100); e.complete();
 with pytest.raises(BusinessRuleViolation): ExecutionPolicyService().can_record(e)
def test_tasks_weighted_progress():
 e=ex(); a=e.add_task('A',2); b=e.add_task('B',1); e.update_task(a.id,100); e.update_task(b.id,0); assert round(e.progress,2)==66.67
def test_task_health():
 e=ex(); t=e.add_task('A'); e.update_task(t.id,50,'red'); assert t.health is HealthStatus.RED
def test_missing_task():
 e=ex();
 with pytest.raises(BusinessRuleViolation): e.update_task(uuid4(),10)
def test_milestones_progress():
 e=ex(); a=e.add_milestone('M1'); b=e.add_milestone('M2'); e.update_milestone(a.id,100); e.update_milestone(b.id,50); assert e.progress==75
def test_resource_consumption():
 e=ex(); e.record_resource_consumption(30); e.record_resource_consumption(20); assert e.resources_consumed==50
def test_budget_spend():
 e=ex(); e.record_budget_spend(250); assert e.budget_spent==250
def test_schedule_variance():
 e=ex(); e.record_schedule_variance(4); assert e.schedule_variance_days==4
def test_signal_validation():
 e=ex(); e.record_signal('negative',3,'delay'); assert len(e.signals)==1
 with pytest.raises(InvalidDomainData): e.record_signal('negative',6)
def test_health_green():
 e=ex(); e.update_progress(100); e.record_budget_spend(0); e.record_resource_consumption(0); e.record_schedule_variance(0); assert e.calculate_health()>=80; assert e.health_status is HealthStatus.GREEN
def test_health_red_with_overrun_signals():
 e=ex(); e.update_progress(20); e.record_budget_spend(1200); e.record_resource_consumption(120); e.record_schedule_variance(20); e.record_signal('negative',5); assert e.calculate_health()<60; assert e.health_status is HealthStatus.RED
def test_health_bounded():
 e=ex(); e.record_budget_spend(10000); e.record_resource_consumption(10000); e.record_signal('negative',5); s=e.calculate_health(); assert 0<=s<=100
def test_rename_event():
 e=ex(); e.pull_events(); e.rename('New Name'); assert e.title=='New Name'; assert isinstance(e.pull_events()[0],ExecutionUpdated)
def test_rename_noop():
 e=ex(); v=e.version; e.rename(e.title); assert e.version==v
def test_version_increments():
 e=ex(); v=e.version; e.update_progress(10); assert e.version==v+1
def test_repo_contract():
 r=InMemoryExecutionRepository(); e=ex(); r.save(e); assert r.get_by_id(e.id) is e; assert r.list_by_project(P)==[e]
def test_repo_uniqueness():
 r=InMemoryExecutionRepository(); e=ex(); r.save(e); assert r.exists_by_title(P,'launch program')
 with pytest.raises(BusinessRuleViolation): ExecutionPolicyService().ensure_unique_title(r,P,'LAUNCH PROGRAM')
def test_repo_exclusion():
 r=InMemoryExecutionRepository(); e=ex(); r.save(e); ExecutionPolicyService().ensure_unique_title(r,P,e.title,e.id)
def test_events_have_actor_and_metadata():
 actor=uuid4(); e=Execution.create(P,'X',actor_id=actor); assert e.pull_events()[0].actor_id==actor
