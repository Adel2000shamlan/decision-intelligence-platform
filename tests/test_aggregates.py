from uuid import uuid4

import pytest

from app.modules.organization.domain.models import Organization
from app.modules.project.domain.models import Project
from app.modules.risk.domain.models import Risk
from app.modules.execution.domain.models import Execution
from app.shared.domain.aggregate import AggregateBoundary, AggregateSnapshot
from app.shared.domain.aggregate_registry import AggregateRegistry
from app.shared.domain.errors import BusinessRuleViolation, InvalidDomainData


def test_domain_roots_expose_stable_aggregate_identity_and_version():
    oid = uuid4()
    org = Organization.create("Org", "org")
    project = Project.create(oid, "Project")
    risk = Risk.create(uuid4(), "Risk")
    execution = Execution.create(uuid4(), "Execution")
    for root in (org, project, risk, execution):
        assert root.aggregate_id == root.id
        assert root.aggregate_version == 1
        root.validate_invariants()


def test_version_guard_rejects_stale_commands():
    org = Organization.create("Org", "org")
    with pytest.raises(BusinessRuleViolation):
        org.assert_version(0)
    org.assert_version(1)


def test_boundary_validation_is_side_effect_free_for_events():
    org = Organization.create("Org", "org")
    assert len(org.pull_events()) == 1
    # New event for validation check.
    org.rename("New Org")
    AggregateBoundary.validate(org)
    assert len(org.pull_events()) == 1


def test_registry_enforces_one_live_root_per_id():
    registry = AggregateRegistry()
    org = Organization.create("Org", "org")
    registry.add(org)
    assert registry.get(org.id) is org
    with pytest.raises(BusinessRuleViolation):
        registry.add(Organization("Other", "other", id=org.id))
    registry.remove(org.id)
    assert len(registry) == 0


def test_snapshot_is_immutable_container():
    org = Organization.create("Org", "org")
    snap = AggregateSnapshot(org.id, org.version, {"name": org.name})
    assert snap.aggregate_id == org.id
    with pytest.raises(Exception):
        snap.version = 99
