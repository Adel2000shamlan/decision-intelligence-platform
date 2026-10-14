from uuid import uuid4

from app.modules.decision.application.implementation import (
    DecisionApplicationService,
)
from app.modules.decision.compatibility.legacy import (
    LegacyMigrationDisposition,
    migrate_legacy_result,
)


def test_migration_result_does_not_execute_or_create_official_decision():
    result = migrate_legacy_result(
        legacy_id="legacy-no-auto-001",
        organization_id=uuid4(),
        project_id=uuid4(),
        title="No auto execution",
        objective="Legacy objective",
        description="Explicit official description",
        legacy_status="draft",
        legacy_version=1,
    )

    assert result.disposition is LegacyMigrationDisposition.CREATE

    service = DecisionApplicationService.in_memory()

    assert service.list() == []
    assert result.payload.title == "No auto execution"
