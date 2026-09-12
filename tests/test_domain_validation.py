from datetime import datetime, timedelta, timezone
from uuid import uuid4
import pytest

from app.shared.domain.errors import InvalidDomainData, BusinessRuleViolation
from app.shared.domain.validation import DomainValidator, DomainValidationError
from app.modules.organization.domain.models import Organization, OrganizationCreated
from app.modules.project.domain.models import Project
from app.modules.risk.domain.models import Risk
from app.modules.execution.domain.models import Execution


def test_all_current_aggregate_roots_pass_validation():
    org = Organization.create("Acme", "acme")
    project = Project.create(org.id, "Project A")
    risk = Risk.create(project.id, "Risk A")
    execution = Execution.create(project.id, "Execution A")
    for aggregate in (org, project, risk, execution):
        DomainValidator.validate_aggregate(aggregate)


def test_validation_is_side_effect_free_for_pending_events():
    org = Organization.create("Acme", "acme")
    before = tuple(org._pending_events)
    DomainValidator.validate_aggregate(org)
    assert tuple(org._pending_events) == before


def test_event_contract_and_sequence():
    org = Organization.create("Acme", "acme")
    events = tuple(org._pending_events)
    DomainValidator.validate_event_sequence(events, org.id)
    bad = OrganizationCreated(uuid4(), datetime.now(timezone.utc), uuid4(), None, "A", "a")
    with pytest.raises(DomainValidationError):
        DomainValidator.validate_event(bad, org.id)


def test_duplicate_event_ids_are_rejected():
    org = Organization.create("Acme", "acme")
    event = org._pending_events[0]
    with pytest.raises(DomainValidationError):
        DomainValidator.validate_event_sequence((event, event), org.id)


def test_invalid_temporal_order_is_rejected():
    org = Organization.create("Acme", "acme")
    org.updated_at = org.created_at - timedelta(seconds=1)
    with pytest.raises(InvalidDomainData):
        DomainValidator.validate_aggregate(org)


def test_future_timestamp_helper():
    with pytest.raises(DomainValidationError):
        DomainValidator.validate_time_now(datetime.now(timezone.utc) + timedelta(minutes=1), "x")


def test_scalar_validation_rejects_bool_and_out_of_range_values():
    with pytest.raises(DomainValidationError):
        DomainValidator.validate_probability_1_5(True, "probability")
    with pytest.raises(DomainValidationError):
        DomainValidator.validate_probability_1_5(6, "probability")
    with pytest.raises(DomainValidationError):
        DomainValidator.validate_numeric_bounds(True, "progress", 0, 100)


def test_validation_requires_timezone_aware_timestamps():
    with pytest.raises(DomainValidationError):
        DomainValidator.validate_timestamp(datetime.now(), "created_at")
