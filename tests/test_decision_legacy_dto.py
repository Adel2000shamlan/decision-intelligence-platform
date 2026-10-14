from uuid import uuid4

import pytest

from app.modules.decision.compatibility.legacy import (
    LegacyDecisionMigration,
    build_legacy_migration,
)
from app.shared.domain.errors import InvalidDomainData


def test_build_legacy_migration_requires_explicit_organization():
    organization_id = uuid4()
    project_id = uuid4()

    migration = build_legacy_migration(
        legacy_id="legacy-123",
        organization_id=organization_id,
        project_id=project_id,
        title="Legacy Decision",
        objective="Grow the business",
        status="submitted",
        version=3,
    )

    assert isinstance(migration, LegacyDecisionMigration)
    assert migration.legacy_id == "legacy-123"
    assert migration.organization_id == organization_id
    assert migration.project_id == project_id
    assert migration.title == "Legacy Decision"
    assert migration.objective == "Grow the business"
    assert migration.official_status.value == "ready_for_approval"
    assert migration.version == 3


def test_objective_is_not_silently_renamed_to_description():
    migration = build_legacy_migration(
        legacy_id="legacy-456",
        organization_id=uuid4(),
        project_id=uuid4(),
        title="Decision",
        objective="Original objective",
        status="draft",
    )

    assert migration.objective == "Original objective"
    assert not hasattr(migration, "description")


def test_archived_decision_cannot_be_migrated():
    with pytest.raises(
        InvalidDomainData,
        match="archived.*no official Decision equivalent",
    ):
        build_legacy_migration(
            legacy_id="legacy-archived",
            organization_id=uuid4(),
            project_id=uuid4(),
            title="Archived Decision",
            objective="Historical objective",
            status="archived",
        )


def test_missing_required_organization_is_rejected():
    with pytest.raises(InvalidDomainData, match="organization_id is required"):
        build_legacy_migration(
            legacy_id="legacy-no-org",
            organization_id=None,
            project_id=uuid4(),
            title="Decision",
            objective="Objective",
            status="draft",
        )
