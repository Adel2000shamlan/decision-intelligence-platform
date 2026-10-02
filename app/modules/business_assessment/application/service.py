from dataclasses import dataclass

from app.modules.business_assessment.application.authorization import (
    BusinessAssessmentAuthorizationAdapter,
)
from app.modules.business_assessment.application.commands import (
    ArchiveBusinessAssessment,
    BusinessAssessmentCommandHandler,
    CompleteBusinessAssessment,
    CreateBusinessAssessment,
    ReturnBusinessAssessmentToDataCollection,
    StartBusinessAssessmentAnalysis,
    StartBusinessAssessmentDataCollection,
    UpdateBusinessAssessmentTitle,
)
from app.modules.business_assessment.application.queries import (
    BusinessAssessmentQueryService,
)
from app.modules.business_assessment.application.validation import (
    BusinessAssessmentApplicationValidator,
)


@dataclass
class BusinessAssessmentApplicationFacade:
    commands: BusinessAssessmentCommandHandler
    queries: BusinessAssessmentQueryService
    authorization: BusinessAssessmentAuthorizationAdapter | None = None

    def create(
        self,
        organization_id,
        title,
        idea_description="",
        actor_id=None,
        tenant_id=None,
    ):
        if self.authorization:
            self.authorization.require(
                "create",
                actor_id,
                tenant_id,
            )

        BusinessAssessmentApplicationValidator.validate_create(
            organization_id,
            title,
            idea_description,
        )

        BusinessAssessmentApplicationValidator.validate_tenant(
            organization_id,
            tenant_id,
        )

        return self.commands.create(
            CreateBusinessAssessment(
                organization_id=organization_id,
                title=title,
                idea_description=idea_description,
                actor_id=actor_id,
                tenant_id=tenant_id,
            )
        )

    def get(
        self,
        assessment_id,
        tenant_id=None,
    ):
        return self.queries.get(
            assessment_id,
            tenant_id,
        )

    def list(
        self,
        organization_id,
        tenant_id=None,
    ):
        return self.queries.list(
            organization_id,
            tenant_id,
        )

    def list_by_status(
        self,
        organization_id,
        status,
        tenant_id=None,
    ):
        BusinessAssessmentApplicationValidator.validate_transition(
            status
        )

        return self.queries.list_by_status(
            organization_id,
            status,
            tenant_id,
        )

    def start_data_collection(
        self,
        assessment_id,
        actor_id=None,
        tenant_id=None,
        expected_version=None,
    ):
        if self.authorization:
            self.authorization.require(
                "start_data_collection",
                actor_id,
                tenant_id,
                assessment_id,
            )

        BusinessAssessmentApplicationValidator.validate_expected_version(
            expected_version
        )

        return self.commands.start_data_collection(
            StartBusinessAssessmentDataCollection(
                assessment_id=assessment_id,
                actor_id=actor_id,
                tenant_id=tenant_id,
                expected_version=expected_version,
            )
        )

    def start_analysis(
        self,
        assessment_id,
        actor_id=None,
        tenant_id=None,
        expected_version=None,
    ):
        if self.authorization:
            self.authorization.require(
                "start_analysis",
                actor_id,
                tenant_id,
                assessment_id,
            )

        BusinessAssessmentApplicationValidator.validate_expected_version(
            expected_version
        )

        return self.commands.start_analysis(
            StartBusinessAssessmentAnalysis(
                assessment_id=assessment_id,
                actor_id=actor_id,
                tenant_id=tenant_id,
                expected_version=expected_version,
            )
        )

    def return_to_data_collection(
        self,
        assessment_id,
        actor_id=None,
        tenant_id=None,
        expected_version=None,
    ):
        if self.authorization:
            self.authorization.require(
                "return_to_data_collection",
                actor_id,
                tenant_id,
                assessment_id,
            )

        BusinessAssessmentApplicationValidator.validate_expected_version(
            expected_version
        )

        return self.commands.return_to_data_collection(
            ReturnBusinessAssessmentToDataCollection(
                assessment_id=assessment_id,
                actor_id=actor_id,
                tenant_id=tenant_id,
                expected_version=expected_version,
            )
        )

    def complete(
        self,
        assessment_id,
        actor_id=None,
        tenant_id=None,
        expected_version=None,
    ):
        if self.authorization:
            self.authorization.require(
                "complete",
                actor_id,
                tenant_id,
                assessment_id,
            )

        BusinessAssessmentApplicationValidator.validate_expected_version(
            expected_version
        )

        return self.commands.complete(
            CompleteBusinessAssessment(
                assessment_id=assessment_id,
                actor_id=actor_id,
                tenant_id=tenant_id,
                expected_version=expected_version,
            )
        )

    def archive(
        self,
        assessment_id,
        actor_id=None,
        tenant_id=None,
        expected_version=None,
    ):
        if self.authorization:
            self.authorization.require(
                "archive",
                actor_id,
                tenant_id,
                assessment_id,
            )

        BusinessAssessmentApplicationValidator.validate_expected_version(
            expected_version
        )

        return self.commands.archive(
            ArchiveBusinessAssessment(
                assessment_id=assessment_id,
                actor_id=actor_id,
                tenant_id=tenant_id,
                expected_version=expected_version,
            )
        )

    def update_title(
        self,
        assessment_id,
        new_title,
        actor_id=None,
        tenant_id=None,
        expected_version=None,
    ):
        if self.authorization:
            self.authorization.require(
                "update",
                actor_id,
                tenant_id,
                assessment_id,
            )

        BusinessAssessmentApplicationValidator.validate_expected_version(
            expected_version
        )

        if not isinstance(new_title, str) or not new_title.strip():
            raise ValueError("invalid business assessment title")

        return self.commands.update_title(
            UpdateBusinessAssessmentTitle(
                assessment_id=assessment_id,
                new_title=new_title,
                actor_id=actor_id,
                tenant_id=tenant_id,
                expected_version=expected_version,
            )
        )
