from uuid import UUID

from app.modules.business_assessment.domain.models import BusinessAssessmentStatus

class BusinessAssessmentApplicationValidationError(ValueError):
    pass

class BusinessAssessmentApplicationValidator:
    @staticmethod
    def validate_create(organization_id, title, idea_description=""):
        if not isinstance(organization_id, UUID):
            raise BusinessAssessmentApplicationValidationError("organization_id must be UUID")
        if not isinstance(title, str) or not title.strip() or len(title.strip()) > 200:
            raise BusinessAssessmentApplicationValidationError("invalid business assessment title")
        if not isinstance(idea_description, str) or len(idea_description.strip()) > 4000:
            raise BusinessAssessmentApplicationValidationError("invalid idea description")

    @staticmethod
    def validate_transition(status):
        try:
            BusinessAssessmentStatus(status)
        except (ValueError, TypeError) as exc:
            raise BusinessAssessmentApplicationValidationError("invalid business assessment status") from exc

    @staticmethod
    def validate_expected_version(version):
        if version is not None and (
            isinstance(version, bool) or
            not isinstance(version, int) or
            version < 1
        ):
            raise BusinessAssessmentApplicationValidationError("expected_version must be positive integer")

    @staticmethod
    def validate_tenant(organization_id, tenant_id):
        if tenant_id is not None and organization_id != tenant_id:
            raise BusinessAssessmentApplicationValidationError("tenant boundary violation")
