from dataclasses import dataclass
from uuid import UUID

from app.shared.domain.errors import EntityNotFound
from app.modules.business_assessment.domain.models import BusinessAssessment, BusinessAssessmentStatus

@dataclass(frozen=True)
class CreateBusinessAssessment:
    organization_id: UUID
    title: str
    idea_description: str = ""
    actor_id: UUID | None = None
    tenant_id: UUID | None = None

@dataclass(frozen=True)
class StartBusinessAssessmentDataCollection:
    assessment_id: UUID
    actor_id: UUID | None = None
    tenant_id: UUID | None = None
    expected_version: int | None = None

@dataclass(frozen=True)
class StartBusinessAssessmentAnalysis:
    assessment_id: UUID
    actor_id: UUID | None = None
    tenant_id: UUID | None = None
    expected_version: int | None = None

@dataclass(frozen=True)
class ReturnBusinessAssessmentToDataCollection:
    assessment_id: UUID
    actor_id: UUID | None = None
    tenant_id: UUID | None = None
    expected_version: int | None = None

@dataclass(frozen=True)
class CompleteBusinessAssessment:
    assessment_id: UUID
    actor_id: UUID | None = None
    tenant_id: UUID | None = None
    expected_version: int | None = None

@dataclass(frozen=True)
class ArchiveBusinessAssessment:
    assessment_id: UUID
    actor_id: UUID | None = None
    tenant_id: UUID | None = None
    expected_version: int | None = None

@dataclass(frozen=True)
class UpdateBusinessAssessmentTitle:
    assessment_id: UUID
    new_title: str
    actor_id: UUID | None = None
    tenant_id: UUID | None = None
    expected_version: int | None = None

@dataclass(frozen=True)
class TransitionBusinessAssessment:
    assessment_id: UUID
    status: BusinessAssessmentStatus
    actor_id: UUID | None = None
    tenant_id: UUID | None = None
    expected_version: int | None = None

class BusinessAssessmentCommandHandler:
    def __init__(self, repository, organization_repository=None, tenant_guard=None, events=None, audit=None):
        if hasattr(repository, "repository") and hasattr(repository, "commit"):
            uow = repository
            repository = uow.repository
            organization_repository = getattr(uow, "organization_repository", organization_repository)
            self._commit = uow.commit
        else:
            self._commit = lambda: None
        if tenant_guard is None:
            from app.modules.business_assessment.application.tenant import BusinessAssessmentTenantGuard
            tenant_guard = BusinessAssessmentTenantGuard()
        self.repository = repository
        self.organization_repository = organization_repository
        self.tenant_guard = tenant_guard
        self.events = events
        self.audit = audit

    def _save(self, assessment, expected_version):
        try:
            return self.repository.save(assessment, expected_version)
        except TypeError:
            return self.repository.save(assessment)

    def _access(self, assessment, tenant_id):
        if self.tenant_guard and tenant_id is not None:
            self.tenant_guard.assert_access(assessment, tenant_id)

    def _get(self, assessment_id, tenant_id=None):
        assessment = self.repository.get_by_id(assessment_id)
        if assessment is None:
            raise EntityNotFound(f"business assessment not found: {assessment_id}")
        self._access(assessment, tenant_id)
        return assessment

    def create(self, command: CreateBusinessAssessment):
        if self.organization_repository is not None:
            organization = self.organization_repository.get_by_id(command.organization_id)
            if organization is None:
                raise EntityNotFound(f"organization not found: {command.organization_id}")
        assessment = BusinessAssessment.create(command.organization_id, command.title, command.idea_description, command.actor_id)
        self._save(assessment, 0)
        self._commit()
        self._post(assessment, command.actor_id, "create")
        return assessment

    def start_data_collection(self, command: StartBusinessAssessmentDataCollection):
        assessment = self._get(command.assessment_id, command.tenant_id)
        old_version = assessment.version
        assessment.start_data_collection(command.actor_id)
        self._save(assessment, command.expected_version if command.expected_version is not None else old_version)
        self._commit()
        self._post(assessment, command.actor_id, "start_data_collection")
        return assessment

    def start_analysis(self, command: StartBusinessAssessmentAnalysis):
        assessment = self._get(command.assessment_id, command.tenant_id)
        old_version = assessment.version
        assessment.start_analysis(command.actor_id)
        self._save(assessment, command.expected_version if command.expected_version is not None else old_version)
        self._commit()
        self._post(assessment, command.actor_id, "start_analysis")
        return assessment

    def return_to_data_collection(self, command: ReturnBusinessAssessmentToDataCollection):
        assessment = self._get(command.assessment_id, command.tenant_id)
        old_version = assessment.version
        assessment.return_to_data_collection(command.actor_id)
        self._save(assessment, command.expected_version if command.expected_version is not None else old_version)
        self._commit()
        self._post(assessment, command.actor_id, "return_to_data_collection")
        return assessment

    def complete(self, command: CompleteBusinessAssessment):
        assessment = self._get(command.assessment_id, command.tenant_id)
        old_version = assessment.version
        assessment.complete(command.actor_id)
        self._save(assessment, command.expected_version if command.expected_version is not None else old_version)
        self._commit()
        self._post(assessment, command.actor_id, "complete")
        return assessment

    def archive(self, command: ArchiveBusinessAssessment):
        assessment = self._get(command.assessment_id, command.tenant_id)
        old_version = assessment.version
        assessment.archive(command.actor_id)
        self._save(assessment, command.expected_version if command.expected_version is not None else old_version)
        self._commit()
        self._post(assessment, command.actor_id, "archive")
        return assessment

    def update_title(self, command: UpdateBusinessAssessmentTitle):
        assessment = self._get(command.assessment_id, command.tenant_id)
        old_version = assessment.version
        assessment.update_title(command.new_title, command.actor_id)
        if assessment.version == old_version:
            return assessment
        self._save(assessment, command.expected_version if command.expected_version is not None else old_version)
        self._commit()
        self._post(assessment, command.actor_id, "update_title")
        return assessment

    def transition(self, command: TransitionBusinessAssessment):
        assessment = self._get(command.assessment_id, command.tenant_id)
        old_version = assessment.version
        transitions = {
            BusinessAssessmentStatus.DATA_COLLECTION: assessment.start_data_collection,
            BusinessAssessmentStatus.UNDER_ANALYSIS: assessment.start_analysis,
            BusinessAssessmentStatus.COMPLETED: assessment.complete,
            BusinessAssessmentStatus.ARCHIVED: assessment.archive,
        }
        action = transitions.get(command.status)
        if action is None:
            raise ValueError(f"unsupported business assessment transition: {command.status}")
        action(command.actor_id)
        self._save(assessment, command.expected_version if command.expected_version is not None else old_version)
        self._commit()
        self._post(assessment, command.actor_id, command.status.value)
        return assessment

    def _post(self, assessment, actor_id, action):
        if self.events:
            for event in assessment.pull_events():
                self.events.publish(event)
        else:
            assessment.pull_events()
        if self.audit:
            self.audit.record(assessment.id, actor_id, action, assessment.version)
