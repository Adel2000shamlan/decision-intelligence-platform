from uuid import uuid4

import pytest

from app.modules.decision.compatibility.legacy import (
    validate_migration_consistency,
)
from app.modules.decision.domain.models import DecisionStatus
from app.shared.domain.errors import InvalidDomainData


def test_matching_status_is_consistent():
    result = validate_migration_consistency(
        legacy_status="approved",
        official_status=DecisionStatus.APPROVED,
    )

    assert result is True


@pytest.mark.parametrize(
    ("legacy_status", "official_status"),
    [
        ("validated", DecisionStatus.ANALYSIS),
        ("submitted", DecisionStatus.READY_FOR_APPROVAL),
        ("rejected", DecisionStatus.REJECTED),
        ("cancelled", DecisionStatus.CANCELLED),
        ("active", DecisionStatus.EXECUTED),
        ("completed", DecisionStatus.CLOSED),
    ],
)
def test_all_supported_status_mappings_can_match(
    legacy_status,
    official_status,
):
    assert (
        validate_migration_consistency(
            legacy_status=legacy_status,
            official_status=official_status,
        )
        is True
    )


def test_mismatched_status_is_rejected():
    with pytest.raises(
        InvalidDomainData,
        match="status mismatch",
    ):
        validate_migration_consistency(
            legacy_status="approved",
            official_status=DecisionStatus.ANALYSIS,
        )


def test_archived_status_is_rejected():
    with pytest.raises(
        InvalidDomainData,
        match="archived",
    ):
        validate_migration_consistency(
            legacy_status="archived",
            official_status=DecisionStatus.CLOSED,
        )


def test_unknown_legacy_status_is_rejected():
    with pytest.raises(
        InvalidDomainData,
        match="unsupported legacy decision status",
    ):
        validate_migration_consistency(
            legacy_status="unknown",
            official_status=DecisionStatus.DRAFT,
        )


def test_none_official_status_is_rejected():
    with pytest.raises(
        InvalidDomainData,
        match="official_status",
    ):
        validate_migration_consistency(
            legacy_status="approved",
            official_status=None,
        )
