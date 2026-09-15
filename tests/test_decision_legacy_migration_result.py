from uuid import uuid4

import pytest

from app.modules.decision.application.commands import CreateDecision
from app.modules.decision.compatibility.legacy import (
    LegacyMigrationDisposition,
    LegacyMigrationResult,
    migrate_legacy_result,
)
from app.modules.decision.domain.models import DecisionStatus
from app.shared.domain.errors import InvalidDomainData


def test_draft_returns_create_result():
    organization_id = uuid4()
    project_id = uuid4()

    result = migrate_legacy_result(
        legacy_id="legacy-draft-result-001",
        organization_id=organization_id,
        project_id=project_id,
        title="New decision",
        objective="Legacy objective",
        description="Official description",
        legacy_status="draft",
        legacy_version=1,
    )

    assert isinstance(result, LegacyMigrationResult)
    assert result.disposition is LegacyMigrationDisposition.CREATE
    assert isinstance(result.payload, CreateDecision)
    assert result.legacy_id == "legacy-draft-result-001"
    assert result.official_status is DecisionStatus.DRAFT


def test_existing_decision_returns_link_result():
    official_id = uuid4()

    result = migrate_legacy_result(
        legacy_id="legacy-approved-result-001",
        organization_id=uuid4(),
        project_id=uuid4(),
        title="Approved decision",
        objective="Existing objective",
        description="Official description",
        legacy_status="approved",
        legacy_version=4,
        official_id=official_id,
        official_status=DecisionStatus.APPROVED,
    )

    assert result.disposition is LegacyMigrationDisposition.LINK
    assert result.legacy_id == "legacy-approved-result-001"
    assert result.official_id == official_id
    assert result.official_status is DecisionStatus.APPROVED
    assert result.payload is not None


def test_archived_returns_explicit_rejection():
    with pytest.raises(
        InvalidDomainData,
        match="archived",
    ):
        migrate_legacy_result(
            legacy_id="legacy-archived-result-001",
            organization_id=uuid4(),
            project_id=uuid4(),
            title="Archived decision",
            objective="Archived objective",
            description="Official description",
            legacy_status="archived",
            legacy_version=9,
            official_id=uuid4(),
            official_status=DecisionStatus.CLOSED,
        )


def test_non_draft_without_official_link_is_rejected():
    with pytest.raises(
        InvalidDomainData,
        match="official_id",
    ):
        migrate_legacy_result(
            legacy_id="legacy-active-result-001",
            organization_id=uuid4(),
            project_id=uuid4(),
            title="Active decision",
            objective="Existing objective",
            description="Official description",
            legacy_status="active",
            legacy_version=5,
        )


def test_result_never_uses_objective_as_description():
    result = migrate_legacy_result(
        legacy_id="legacy-draft-result-002",
        organization_id=uuid4(),
        project_id=uuid4(),
        title="Decision",
        objective="Legacy objective",
        description="Explicit official description",
        legacy_status="draft",
        legacy_version=2,
    )

    assert isinstance(result.payload, CreateDecision)
    assert result.payload.description == "Explicit official description"
    assert result.payload.description != "Legacy objective"
