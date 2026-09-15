from uuid import uuid4

from app.modules.decision.application.commands import CreateDecision
from app.modules.decision.compatibility.legacy import (
    LegacyMigrationDisposition,
    LegacyMigrationResult,
    migrate_legacy_result,
)


def test_create_result_is_application_command_without_executing_it():
    result = migrate_legacy_result(
        legacy_id="legacy-boundary-001",
        organization_id=uuid4(),
        project_id=uuid4(),
        title="Boundary decision",
        objective="Legacy objective",
        description="Explicit official description",
        legacy_status="draft",
        legacy_version=1,
    )

    assert isinstance(result, LegacyMigrationResult)
    assert result.disposition is LegacyMigrationDisposition.CREATE
    assert isinstance(result.payload, CreateDecision)
    assert result.legacy_id == "legacy-boundary-001"
