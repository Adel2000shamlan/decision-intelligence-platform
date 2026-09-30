from uuid import UUID

from app.modules.business_assessment.domain.models import BusinessAssessment


class BusinessAssessmentTenantGuard:
    @staticmethod
    def assert_access(
        assessment: BusinessAssessment,
        organization_id: UUID,
    ) -> None:
        if assessment.organization_id != organization_id:
            raise PermissionError(
                "business assessment tenant boundary violation"
            )
