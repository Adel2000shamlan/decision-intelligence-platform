from dataclasses import dataclass
from uuid import UUID

from app.modules.decision.application.commands import (
    ApproveDecision,
    CancelDecision,
    CloseDecision,
    CreateDecision,
    DecisionCommandHandler,
    ExecuteDecision,
    RejectDecision,
    StartDecisionAnalysis,
    SubmitDecisionForApproval,
    UpdateDecision,
)
from app.modules.decision.application.ports import DecisionUnitOfWork
from app.modules.decision.domain.models import DecisionPriority, DecisionType
from app.modules.decision.domain.services import DecisionPolicyService
from app.modules.decision.in_memory import (
    DefaultDecisionFactory,
    InMemoryDecisionRepository,
)


@dataclass
class DecisionApplicationService:
    commands: DecisionCommandHandler

    @classmethod
    def from_repository(cls, repository) -> "DecisionApplicationService":
        uow = DecisionUnitOfWork(
            repository=repository,
            factory=DefaultDecisionFactory(),
            policy=DecisionPolicyService(),
        )
        return cls(DecisionCommandHandler(uow))

    @classmethod
    def in_memory(cls) -> "DecisionApplicationService":
        return cls.from_repository(InMemoryDecisionRepository())

    @property
    def repository(self):
        return self.commands.uow.repository

    def create(
        self,
        organization_id: UUID,
        project_id: UUID,
        title: str,
        description: str = "",
        decision_type: DecisionType = DecisionType.STRATEGIC,
        priority: DecisionPriority = DecisionPriority.MEDIUM,
        actor_id: UUID | None = None,
    ):
        return self.commands.create(
            CreateDecision(
                organization_id=organization_id,
                project_id=project_id,
                title=title,
                description=description,
                decision_type=decision_type,
                priority=priority,
                actor_id=actor_id,
            )
        )

    def get(self, decision_id: UUID):
        return self.repository.get_by_id(decision_id)

    def list(self, organization_id: UUID | None = None):
        if organization_id is None:
            return self.repository.list_all()
        return self.repository.list_by_organization(organization_id)

    def start_analysis(
        self,
        decision_id: UUID,
        actor_id: UUID | None = None,
        expected_version: int | None = None,
    ):
        return self.commands.start_analysis(
            StartDecisionAnalysis(
                decision_id,
                actor_id,
                expected_version,
            )
        )

    def submit_for_approval(
        self,
        decision_id: UUID,
        actor_id: UUID | None = None,
        expected_version: int | None = None,
    ):
        return self.commands.submit_for_approval(
            SubmitDecisionForApproval(
                decision_id,
                actor_id,
                expected_version,
            )
        )

    def approve(
        self,
        decision_id: UUID,
        actor_id: UUID | None = None,
        expected_version: int | None = None,
    ):
        return self.commands.approve(
            ApproveDecision(
                decision_id,
                actor_id,
                expected_version,
            )
        )

    def reject(
        self,
        decision_id: UUID,
        reason: str | None = None,
        actor_id: UUID | None = None,
        expected_version: int | None = None,
    ):
        return self.commands.reject(
            RejectDecision(
                decision_id,
                reason,
                actor_id,
                expected_version,
            )
        )

    def cancel(
        self,
        decision_id: UUID,
        reason: str | None = None,
        actor_id: UUID | None = None,
        expected_version: int | None = None,
    ):
        return self.commands.cancel(
            CancelDecision(
                decision_id,
                reason,
                actor_id,
                expected_version,
            )
        )

    def execute(
        self,
        decision_id: UUID,
        actor_id: UUID | None = None,
        expected_version: int | None = None,
    ):
        return self.commands.execute(
            ExecuteDecision(
                decision_id,
                actor_id,
                expected_version,
            )
        )

    def close(
        self,
        decision_id: UUID,
        actor_id: UUID | None = None,
        expected_version: int | None = None,
    ):
        return self.commands.close(
            CloseDecision(
                decision_id,
                actor_id,
                expected_version,
            )
        )

    def update(
        self,
        decision_id: UUID,
        field_name: str,
        value: object,
        actor_id: UUID | None = None,
        expected_version: int | None = None,
    ):
        return self.commands.update(
            UpdateDecision(
                decision_id,
                field_name,
                value,
                actor_id,
                expected_version,
            )
        )
