from uuid import uuid4

import pytest

from app.modules.decision.application.commands import CreateDecision
from app.modules.decision.compatibility.legacy import (
    build_legacy_migration,
    to_create_command,
)
from app.shared.domain.errors import InvalidDomainData


def test_legacy_adapter_builds_official_create_command():
    organization_id = uuid4()
    project_id = uuid4()
    actor_id = uuid4()

    migration = build_legacy_migration(
        legacy_id="legacy-001",
        organization_id=organization_id,
        project_id=project_id,
        title="Legacy Decision",
        objective="Legacy objective",
        status="draft",
        version=1,
    )

    command = to_create_command(
        migration,
        description="Explicit official description",
        actor_id=actor_id,
    )

    assert isinstance(command, CreateDecision)
    assert command.organization_id == organization_id
    assert command.project_id == project_id
    assert command.title == "Legacy Decision"
    assert command.description == "Explicit official description"
    assert command.actor_id == actor_id


def test_legacy_objective_is_not_used_as_official_description():
    migration = build_legacy_migration(
        legacy_id="legacy-002",
        organization_id=uuid4(),
        project_id=uuid4(),
        title="Decision",
        objective="Legacy objective",
        status="draft",
    )

    with pytest.raises(
        InvalidDomainData,
        match="explicit official description is required",
    ):
        to_create_command(migration)


def test_legacy_archived_decision_cannot_reach_official_command():
    with pytest.raises(
        InvalidDomainData,
        match="archived.*no official Decision equivalent",
    ):
        migration = build_legacy_migration(
            legacy_id="legacy-003",
            organization_id=uuid4(),
            project_id=uuid4(),
            title="Archived Decision",
            objective="Historical objective",
            status="archived",
        )
        to_create_command(migration, description="Historical decision")


def test_legacy_migration_version_is_not_reused_as_official_version():
    migration = build_legacy_migration(
        legacy_id="legacy-004",
        organization_id=uuid4(),
        project_id=uuid4(),
        title="Decision",
        objective="Objective",
        status="draft",
        version=7,
    )

    command = to_create_command(
        migration,
        description="Explicit description",
    )

    assert command.organization_id == migration.organization_id
    assert not hasattr(command, "version")


@pytest.mark.parametrize(
    "status",
    [
        "validated",
        "submitted",
        "approved",
        "rejected",
        "cancelled",
        "active",
        "completed",
    ],
)
def test_non_draft_legacy_decision_cannot_be_created_as_new_official_decision(status):
    migration = build_legacy_migration(
        legacy_id=f"legacy-{status}",
        organization_id=uuid4(),
        project_id=uuid4(),
        title=f"Decision {status}",
        objective="Legacy objective",
        status=status,
    )

    with pytest.raises(
        InvalidDomainData,
        match="only legacy decisions mapped to official draft",
    ):
        to_create_command(
            migration,
            description="Explicit official description",
        )
