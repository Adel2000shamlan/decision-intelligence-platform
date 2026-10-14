from uuid import uuid4

import pytest

from app.modules.decision.compatibility.legacy import (
    LegacyMigrationDisposition,
    evaluate_migration_policy,
)
from app.shared.domain.errors import InvalidDomainData


def test_draft_legacy_decision_is_migratable():
    result = evaluate_migration_policy(
        status="draft",
        organization_id=uuid4(),
    )

    assert result.disposition is LegacyMigrationDisposition.MIGRATABLE
    assert result.official_status.value == "draft"


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
def test_non_draft_status_is_known_but_requires_existing_decision_migration(
    status,
    official_status,
):
    result = evaluate_migration_policy(
        status=status,
        organization_id=uuid4(),
    )

    assert result.disposition is LegacyMigrationDisposition.REQUIRES_EXISTING_MIGRATION
    assert result.official_status.value == official_status


def test_archived_legacy_decision_is_not_migratable():
    result = evaluate_migration_policy(
        status="archived",
        organization_id=uuid4(),
    )

    assert result.disposition is LegacyMigrationDisposition.UNSUPPORTED
    assert result.official_status is None
    assert result.reason


def test_missing_organization_blocks_migration():
    result = evaluate_migration_policy(
        status="draft",
        organization_id=None,
    )

    assert result.disposition is LegacyMigrationDisposition.BLOCKED
    assert result.official_status is None
    assert "organization_id" in result.reason


def test_unknown_status_is_rejected():
    with pytest.raises(
        InvalidDomainData,
        match="unsupported legacy decision status",
    ):
        evaluate_migration_policy(
            status="unknown",
            organization_id=uuid4(),
        )
