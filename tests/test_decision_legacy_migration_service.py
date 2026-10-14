from uuid import uuid4

import pytest

from app.modules.decision.application.commands import CreateDecision
from app.modules.decision.compatibility.legacy import (
    migrate_legacy_draft,
)
from app.shared.domain.errors import InvalidDomainData


def test_migrate_legacy_draft_creates_official_command():
    organization_id = uuid4()
    project_id = uuid4()

    command = migrate_legacy_draft(
        legacy_id="legacy-001",
        organization_id=organization_id,
        project_id=project_id,
        title="Business expansion",
        objective="Evaluate expansion feasibility",
        description="Explicit official description",
        status="draft",
        legacy_version=7,
    )

    assert isinstance(command, CreateDecision)
    assert command.organization_id == organization_id
    assert command.project_id == project_id
    assert command.title == "Business expansion"
    assert command.description == "Explicit official description"


def test_objective_is_not_silently_used_as_description():
    command = migrate_legacy_draft(
        legacy_id="legacy-002",
        organization_id=uuid4(),
        project_id=uuid4(),
        title="Decision",
        objective="Legacy objective",
        description="Official description",
        status="draft",
        legacy_version=3,
    )

    assert command.description == "Official description"
    assert command.description != "Legacy objective"


def test_non_draft_cannot_use_new_creation_path():
    with pytest.raises(
        InvalidDomainData,
        match="only.*draft",
    ):
        migrate_legacy_draft(
            legacy_id="legacy-003",
            organization_id=uuid4(),
            project_id=uuid4(),
            title="Approved decision",
            objective="Existing objective",
            description="Official description",
            status="approved",
            legacy_version=4,
        )


def test_archived_cannot_be_migrated():
    with pytest.raises(
        InvalidDomainData,
        match="archived",
    ):
        migrate_legacy_draft(
            legacy_id="legacy-004",
            organization_id=uuid4(),
            project_id=uuid4(),
            title="Archived decision",
            objective="Archived objective",
            description="Official description",
            status="archived",
            legacy_version=9,
        )


def test_explicit_description_is_required():
    with pytest.raises(
        InvalidDomainData,
        match="description",
    ):
        migrate_legacy_draft(
            legacy_id="legacy-005",
            organization_id=uuid4(),
            project_id=uuid4(),
            title="Decision",
            objective="Objective",
            description="",
            status="draft",
            legacy_version=1,
        )
