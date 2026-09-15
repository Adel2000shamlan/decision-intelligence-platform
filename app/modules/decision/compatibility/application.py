from __future__ import annotations

from app.modules.decision.application.implementation import (
    DecisionApplicationService,
)
from app.modules.decision.compatibility.legacy import (
    LegacyMigrationDisposition,
    LegacyMigrationResult,
)


class LegacyDecisionApplicationAdapter:
    def __init__(self, application_service: DecisionApplicationService):
        self.application_service = application_service

    def execute(self, result: LegacyMigrationResult):
        if not isinstance(result, LegacyMigrationResult):
            raise TypeError("result must be LegacyMigrationResult")

        if result.disposition is not LegacyMigrationDisposition.CREATE:
            raise ValueError(
                "only CREATE migration results can be executed"
            )

        command = result.payload

        return self.application_service.create(
            organization_id=command.organization_id,
            project_id=command.project_id,
            title=command.title,
            description=command.description,
            decision_type=command.decision_type,
            priority=command.priority,
            actor_id=command.actor_id,
        )
