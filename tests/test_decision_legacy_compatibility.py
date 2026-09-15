import pytest

from app.modules.decision.compatibility.legacy import (
    can_migrate_status,
    to_official_status,
)
from app.shared.domain.errors import InvalidDomainData


@pytest.mark.parametrize(
    ("legacy", "official"),
    [
        ("draft", "draft"),
        ("validated", "analysis"),
        ("submitted", "ready_for_approval"),
        ("approved", "approved"),
        ("rejected", "rejected"),
        ("cancelled", "cancelled"),
        ("active", "executed"),
        ("completed", "closed"),
    ],
)
def test_legacy_status_maps_to_official_status(legacy, official):
    assert to_official_status(legacy).value == official
    assert can_migrate_status(legacy)


def test_archived_has_no_official_equivalent():
    assert not can_migrate_status("archived")

    with pytest.raises(
        InvalidDomainData,
        match="archived.*no official Decision equivalent",
    ):
        to_official_status("archived")


@pytest.mark.parametrize("status", ["unknown", "", None])
def test_unsupported_legacy_status_is_rejected(status):
    assert not can_migrate_status(status)

    with pytest.raises(InvalidDomainData, match="unsupported legacy decision status"):
        to_official_status(status)
