from uuid import uuid4

import pytest

from app.modules.decision.compatibility.legacy import (
    LegacyMigrationLink,
    build_migration_link,
)
from app.shared.domain.errors import InvalidDomainData


def test_valid_link_preserves_both_ids():
    legacy_id = "legacy-001"
    official_id = uuid4()

    link = build_migration_link(
        legacy_id=legacy_id,
        official_id=official_id,
        legacy_status="approved",
    )

    assert isinstance(link, LegacyMigrationLink)
    assert link.legacy_id == legacy_id
    assert link.official_id == official_id
    assert link.official_status.value == "approved"


@pytest.mark.parametrize(
    ("legacy_status", "official_status"),
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
def test_link_maps_known_legacy_status(
    legacy_status,
    official_status,
):
    link = build_migration_link(
        legacy_id="legacy-002",
        official_id=uuid4(),
        legacy_status=legacy_status,
    )

    assert link.official_status.value == official_status


def test_draft_does_not_use_link_path():
    with pytest.raises(
        InvalidDomainData,
        match="draft.*create",
    ):
        build_migration_link(
            legacy_id="legacy-003",
            official_id=uuid4(),
            legacy_status="draft",
        )


def test_archived_cannot_be_linked():
    with pytest.raises(
        InvalidDomainData,
        match="archived",
    ):
        build_migration_link(
            legacy_id="legacy-004",
            official_id=uuid4(),
            legacy_status="archived",
        )


def test_missing_legacy_id_is_rejected():
    with pytest.raises(
        InvalidDomainData,
        match="legacy_id",
    ):
        build_migration_link(
            legacy_id="",
            official_id=uuid4(),
            legacy_status="approved",
        )


def test_missing_official_id_is_rejected():
    with pytest.raises(
        InvalidDomainData,
        match="official_id",
    ):
        build_migration_link(
            legacy_id="legacy-005",
            official_id=None,
            legacy_status="approved",
        )
