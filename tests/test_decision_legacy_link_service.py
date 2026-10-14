from uuid import uuid4

import pytest

from app.modules.decision.compatibility.legacy import (
    LegacyMigrationLink,
    link_legacy_decision,
)
from app.modules.decision.domain.models import DecisionStatus
from app.shared.domain.errors import InvalidDomainData


def test_link_legacy_decision_returns_existing_official_link():
    official_id = uuid4()

    link = link_legacy_decision(
        legacy_id="legacy-approved-001",
        legacy_status="approved",
        official_id=official_id,
        official_status=DecisionStatus.APPROVED,
    )

    assert isinstance(link, LegacyMigrationLink)
    assert link.legacy_id == "legacy-approved-001"
    assert link.official_id == official_id
    assert link.official_status is DecisionStatus.APPROVED


def test_link_legacy_decision_preserves_status_mapping():
    official_id = uuid4()

    link = link_legacy_decision(
        legacy_id="legacy-active-001",
        legacy_status="active",
        official_id=official_id,
        official_status=DecisionStatus.EXECUTED,
    )

    assert link.official_status is DecisionStatus.EXECUTED


def test_link_requires_existing_official_decision():
    with pytest.raises(
        InvalidDomainData,
        match="official_id",
    ):
        link_legacy_decision(
            legacy_id="legacy-approved-002",
            legacy_status="approved",
            official_id=None,
            official_status=DecisionStatus.APPROVED,
        )


def test_link_rejects_status_mismatch():
    with pytest.raises(
        InvalidDomainData,
        match="status mismatch",
    ):
        link_legacy_decision(
            legacy_id="legacy-approved-003",
            legacy_status="approved",
            official_id=uuid4(),
            official_status=DecisionStatus.EXECUTED,
        )


def test_link_rejects_draft():
    with pytest.raises(
        InvalidDomainData,
        match="draft",
    ):
        link_legacy_decision(
            legacy_id="legacy-draft-001",
            legacy_status="draft",
            official_id=uuid4(),
            official_status=DecisionStatus.DRAFT,
        )


def test_link_rejects_archived():
    with pytest.raises(
        InvalidDomainData,
        match="archived",
    ):
        link_legacy_decision(
            legacy_id="legacy-archived-001",
            legacy_status="archived",
            official_id=uuid4(),
            official_status=DecisionStatus.CLOSED,
        )


@pytest.mark.parametrize(
    ("legacy_status", "official_status"),
    [
        ("validated", DecisionStatus.ANALYSIS),
        ("submitted", DecisionStatus.READY_FOR_APPROVAL),
        ("rejected", DecisionStatus.REJECTED),
        ("cancelled", DecisionStatus.CANCELLED),
        ("completed", DecisionStatus.CLOSED),
    ],
)
def test_link_supports_all_mappable_non_draft_statuses(
    legacy_status,
    official_status,
):
    link = link_legacy_decision(
        legacy_id=f"legacy-{legacy_status}-001",
        legacy_status=legacy_status,
        official_id=uuid4(),
        official_status=official_status,
    )

    assert link.official_status is official_status
