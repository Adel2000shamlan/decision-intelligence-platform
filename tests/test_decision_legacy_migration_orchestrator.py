from uuid import uuid4

import pytest

from app.modules.decision.application.commands import CreateDecision
from app.modules.decision.compatibility.legacy import (
    LegacyMigrationLink,
    migrate_legacy_decision,
)
from app.modules.decision.domain.models import DecisionStatus
from app.shared.domain.errors import InvalidDomainData


def test_orchestrator_uses_create_path_for_draft():
    organization_id = uuid4()
    project_id = uuid4()

    result = migrate_legacy_decision(
        legacy_id="legacy-draft-001",
        organization_id=organization_id,
        project_id=project_id,
        title="New decision",
        objective="Legacy objective",
        description="Official description",
        legacy_status="draft",
        legacy_version=1,
    )

    assert isinstance(result, CreateDecision)
    assert result.organization_id == organization_id
    assert result.project_id == project_id
    assert result.description == "Official description"


def test_orchestrator_uses_link_path_for_existing_decision():
    official_id = uuid4()

    result = migrate_legacy_decision(
        legacy_id="legacy-approved-001",
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

    assert isinstance(result, LegacyMigrationLink)
    assert result.official_id == official_id
    assert result.official_status is DecisionStatus.APPROVED


def test_orchestrator_rejects_non_draft_without_existing_official():
    with pytest.raises(
        InvalidDomainData,
        match="official_id",
    ):
        migrate_legacy_decision(
            legacy_id="legacy-approved-002",
            organization_id=uuid4(),
            project_id=uuid4(),
            title="Approved decision",
            objective="Existing objective",
            description="Official description",
            legacy_status="approved",
            legacy_version=4,
        )


def test_orchestrator_rejects_archived():
    with pytest.raises(
        InvalidDomainData,
        match="archived",
    ):
        migrate_legacy_decision(
            legacy_id="legacy-archived-001",
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


def test_orchestrator_rejects_status_mismatch():
    with pytest.raises(
        InvalidDomainData,
        match="status mismatch",
    ):
        migrate_legacy_decision(
            legacy_id="legacy-approved-003",
            organization_id=uuid4(),
            project_id=uuid4(),
            title="Approved decision",
            objective="Existing objective",
            description="Official description",
            legacy_status="approved",
            legacy_version=4,
            official_id=uuid4(),
            official_status=DecisionStatus.EXECUTED,
        )


def test_orchestrator_requires_explicit_description_for_draft():
    with pytest.raises(
        InvalidDomainData,
        match="description",
    ):
        migrate_legacy_decision(
            legacy_id="legacy-draft-002",
            organization_id=uuid4(),
            project_id=uuid4(),
            title="Decision",
            objective="Objective",
            description="",
            legacy_status="draft",
            legacy_version=1,
        )


def test_orchestrator_does_not_create_for_non_draft_even_with_description():
    with pytest.raises(
        InvalidDomainData,
        match="official_id",
    ):
        migrate_legacy_decision(
            legacy_id="legacy-active-001",
            organization_id=uuid4(),
            project_id=uuid4(),
            title="Active decision",
            objective="Existing objective",
            description="Official description",
            legacy_status="active",
            legacy_version=5,
        )
