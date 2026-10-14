from uuid import uuid4

import pytest

from app.modules.decision.compatibility.legacy import (
    LegacyMigrationDisposition,
    build_migration_plan,
)


def test_draft_plan_is_create_new_official_decision():
    plan = build_migration_plan(
        legacy_id="legacy-001",
        status="draft",
        organization_id=uuid4(),
    )

    assert plan.disposition is LegacyMigrationDisposition.MIGRATABLE
    assert plan.action == "create_official_decision"
    assert plan.official_status.value == "draft"


@pytest.mark.parametrize(
    ("status", "official_status"),
    [
        ("validated", "analysis"),
        ("submitted", "ready_for_approval"),
        ("approved", "approved"),
        ("rejected", "rejected"),
        ("cancelled", "cancelled"),
        ("active", "executed"),
        ("completed", "closed"),
    ],
)
def test_existing_status_requires_existing_official_decision(
    status,
    official_status,
):
    plan = build_migration_plan(
        legacy_id="legacy-002",
        status=status,
        organization_id=uuid4(),
    )

    assert (
        plan.disposition
        is LegacyMigrationDisposition.REQUIRES_EXISTING_MIGRATION
    )
    assert plan.action == "link_existing_official_decision"
    assert plan.official_status.value == official_status


def test_archived_plan_is_unsupported():
    plan = build_migration_plan(
        legacy_id="legacy-003",
        status="archived",
        organization_id=uuid4(),
    )

    assert plan.disposition is LegacyMigrationDisposition.UNSUPPORTED
    assert plan.action == "reject_migration"
    assert plan.official_status is None


def test_missing_organization_blocks_plan():
    plan = build_migration_plan(
        legacy_id="legacy-004",
        status="draft",
        organization_id=None,
    )

    assert plan.disposition is LegacyMigrationDisposition.BLOCKED
    assert plan.action == "block_migration"
    assert plan.official_status is None


def test_legacy_id_is_required():
    with pytest.raises(ValueError, match="legacy_id"):
        build_migration_plan(
            legacy_id="",
            status="draft",
            organization_id=uuid4(),
        )
