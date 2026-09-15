from uuid import uuid4

from app.modules.decision.application.implementation import (
    DecisionApplicationService,
)
from app.modules.decision.compatibility.legacy import (
    LegacyMigrationDisposition,
    migrate_legacy_result,
)


def test_legacy_create_result_can_be_explicitly_executed_by_application_service():
    organization_id = uuid4()
    project_id = uuid4()

    result = migrate_legacy_result(
        legacy_id="legacy-execution-001",
        organization_id=organization_id,
        project_id=project_id,
        title="Execution boundary decision",
        objective="Legacy objective",
        description="Explicit official description",
        legacy_status="draft",
        legacy_version=1,
    )

    assert result.disposition is LegacyMigrationDisposition.CREATE

    service = DecisionApplicationService.in_memory()
    command = result.payload

    decision = service.create(
        organization_id=command.organization_id,
        project_id=command.project_id,
        title=command.title,
        description=command.description,
        decision_type=command.decision_type,
        priority=command.priority,
        actor_id=command.actor_id,
    )

    assert decision.organization_id == organization_id
    assert decision.project_id == project_id
    assert decision.title == "Execution boundary decision"
    assert decision.description == "Explicit official description"
