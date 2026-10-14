from uuid import uuid4

import pytest

from app.modules.decision.compatibility.legacy import (
    validate_migration_input,
)
from app.shared.domain.errors import InvalidDomainData


def test_complete_draft_input_is_valid():
    result = validate_migration_input(
        legacy_id="legacy-001",
        organization_id=uuid4(),
        project_id=uuid4(),
        title="Expand the business",
        objective="Evaluate expansion feasibility",
        status="draft",
    )

    assert result.legacy_id == "legacy-001"
    assert result.organization_id is not None
    assert result.project_id is not None
    assert result.title == "Expand the business"
    assert result.objective == "Evaluate expansion feasibility"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("legacy_id", ""),
        ("title", ""),
        ("objective", ""),
    ],
)
def test_required_text_fields_are_rejected(field, value):
    data = {
        "legacy_id": "legacy-002",
        "organization_id": uuid4(),
        "project_id": uuid4(),
        "title": "Valid title",
        "objective": "Valid objective",
        "status": "draft",
    }
    data[field] = value

    with pytest.raises(InvalidDomainData):
        validate_migration_input(**data)


def test_missing_organization_is_rejected():
    with pytest.raises(
        InvalidDomainData,
        match="organization_id",
    ):
        validate_migration_input(
            legacy_id="legacy-003",
            organization_id=None,
            project_id=uuid4(),
            title="Valid title",
            objective="Valid objective",
            status="draft",
        )


def test_missing_project_is_rejected():
    with pytest.raises(
        InvalidDomainData,
        match="project_id",
    ):
        validate_migration_input(
            legacy_id="legacy-004",
            organization_id=uuid4(),
            project_id=None,
            title="Valid title",
            objective="Valid objective",
            status="draft",
        )


def test_non_draft_status_is_valid_input_but_not_new_creation():
    result = validate_migration_input(
        legacy_id="legacy-005",
        organization_id=uuid4(),
        project_id=uuid4(),
        title="Existing decision",
        objective="Existing objective",
        status="approved",
    )

    assert result.official_status.value == "approved"


def test_archived_status_is_rejected():
    with pytest.raises(
        InvalidDomainData,
        match="archived",
    ):
        validate_migration_input(
            legacy_id="legacy-006",
            organization_id=uuid4(),
            project_id=uuid4(),
            title="Archived decision",
            objective="Archived objective",
            status="archived",
        )
