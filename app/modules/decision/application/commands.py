from dataclasses import dataclass
from uuid import UUID

from app.shared.domain.errors import EntityNotFound, BusinessRuleViolation

from .ports import DecisionUnitOfWork
from ..domain.models import DecisionType, DecisionPriority
from ..domain.services import DecisionDomainService


@dataclass(frozen=True)
class CreateDecision:
    organization_id: UUID
    project_id: UUID
    title: str
    description: str = ""
    decision_type: DecisionType = DecisionType.STRATEGIC
    priority: DecisionPriority = DecisionPriority.MEDIUM
    actor_id: UUID | None = None


@dataclass(frozen=True)
class StartDecisionAnalysis:
    decision_id: UUID
    actor_id: UUID | None = None
    expected_version: int | None = None


@dataclass(frozen=True)
class SubmitDecisionForApproval:
    decision_id: UUID
    actor_id: UUID | None = None
    expected_version: int | None = None


@dataclass(frozen=True)
class ApproveDecision:
    decision_id: UUID
    actor_id: UUID | None = None
    expected_version: int | None = None


@dataclass(frozen=True)
class RejectDecision:
    decision_id: UUID
    reason: str | None = None
    actor_id: UUID | None = None
    expected_version: int | None = None


@dataclass(frozen=True)
class CancelDecision:
    decision_id: UUID
    reason: str | None = None
    actor_id: UUID | None = None
    expected_version: int | None = None


@dataclass(frozen=True)
class ExecuteDecision:
    decision_id: UUID
    actor_id: UUID | None = None
    expected_version: int | None = None


@dataclass(frozen=True)
class CloseDecision:
    decision_id: UUID
    actor_id: UUID | None = None
    expected_version: int | None = None


@dataclass(frozen=True)
class UpdateDecision:
    decision_id: UUID
    field_name: str
    value: object
    actor_id: UUID | None = None
    expected_version: int | None = None


class DecisionCommandHandler:
    def __init__(
        self,
        uow: DecisionUnitOfWork,
        domain_service: DecisionDomainService | None = None,
    ):
        self.uow = uow
        self.domain_service = domain_service or DecisionDomainService()

    def _get(self, decision_id: UUID):
        decision = self.uow.repository.get_by_id(decision_id)
        if decision is None:
            raise EntityNotFound(f"decision not found: {decision_id}")
        return decision

    def _commit_result(self, result):
        self.uow.commit()
        return result.entity

    def create(self, command: CreateDecision):
        result = self.domain_service.create(
            repository=self.uow.repository,
            organization_id=command.organization_id,
            project_id=command.project_id,
            title=command.title,
            description=command.description,
            decision_type=command.decision_type,
            priority=command.priority,
            actor_id=command.actor_id,
        )
        self.uow.commit()
        return result.entity

    def start_analysis(self, command: StartDecisionAnalysis):
        result = self.domain_service.start_analysis(
            self.uow.repository,
            command.decision_id,
            command.actor_id,
            command.expected_version,
        )
        return self._commit_result(result)

    def submit_for_approval(self, command: SubmitDecisionForApproval):
        decision = self._get(command.decision_id)
        self.uow.policy.ensure_can_submit(decision)

        result = self.domain_service.submit_for_approval(
            self.uow.repository,
            command.decision_id,
            command.actor_id,
            command.expected_version,
        )
        return self._commit_result(result)

    def approve(self, command: ApproveDecision):
        decision = self._get(command.decision_id)
        self.uow.policy.ensure_can_approve(decision)

        result = self.domain_service.approve(
            self.uow.repository,
            command.decision_id,
            command.actor_id,
            command.expected_version,
        )
        return self._commit_result(result)

    def reject(self, command: RejectDecision):
        result = self.domain_service.reject(
            self.uow.repository,
            command.decision_id,
            command.reason,
            command.actor_id,
            command.expected_version,
        )
        return self._commit_result(result)

    def cancel(self, command: CancelDecision):
        result = self.domain_service.cancel(
            self.uow.repository,
            command.decision_id,
            command.reason,
            command.actor_id,
            command.expected_version,
        )
        return self._commit_result(result)

    def execute(self, command: ExecuteDecision):
        result = self.domain_service.execute(
            self.uow.repository,
            command.decision_id,
            command.actor_id,
            command.expected_version,
        )
        return self._commit_result(result)

    def close(self, command: CloseDecision):
        result = self.domain_service.close(
            self.uow.repository,
            command.decision_id,
            command.actor_id,
            command.expected_version,
        )
        return self._commit_result(result)

    def update(self, command: UpdateDecision):
        decision = self._get(command.decision_id)

        if (
            command.field_name == "title"
            and isinstance(command.value, str)
            and command.value.strip() != decision.title
            and self.uow.repository.exists_by_title(
                decision.project_id,
                command.value,
            )
        ):
            raise BusinessRuleViolation(
                f"decision title already exists in project: {command.value.strip()}"
            )

        result = self.domain_service.update(
            self.uow.repository,
            command.decision_id,
            command.field_name,
            command.value,
            command.actor_id,
            command.expected_version,
        )
        return self._commit_result(result)
