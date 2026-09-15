from __future__ import annotations

from app.modules.decision.application.implementation import (
    DecisionApplicationService,
)
from app.modules.decision.application.commands import CreateDecision
from app.modules.decision.compatibility.legacy import (
    LegacyMigrationDisposition,
    LegacyMigrationResult,
)


class LegacyDecisionApplicationAdapter:
    """Explicit execution boundary from legacy migration to the official application layer.

    Migration produces a result only; it never executes an official decision implicitly.
    Only a validated CREATE result carrying a CreateDecision command may be executed.
    """
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
        if not isinstance(command, CreateDecision):
            raise TypeError("payload must be CreateDecision")

        return self.application_service.create(
            organization_id=command.organization_id,
            project_id=command.project_id,
            title=command.title,
            description=command.description,
            decision_type=command.decision_type,
            priority=command.priority,
            actor_id=command.actor_id,
        )
