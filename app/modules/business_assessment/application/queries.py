from dataclasses import dataclass
from uuid import UUID

from app.shared.domain.errors import EntityNotFound
from app.modules.business_assessment.domain.models import (
    BusinessAssessmentStatus,
)


@dataclass
class BusinessAssessmentQueryService:
    repository: object

    def get(
        self,
        assessment_id: UUID,
        tenant_id: UUID | None = None,
    ):
        assessment = self.repository.get_by_id(assessment_id)

        if assessment is None:
            raise EntityNotFound(
                f"business assessment not found: {assessment_id}"
            )

        if tenant_id is not None:
            if assessment.organization_id != tenant_id:
                raise PermissionError(
                    "business assessment tenant boundary violation"
                )

        return assessment

    def list(
        self,
        organization_id: UUID,
        tenant_id: UUID | None = None,
    ):
        if tenant_id is not None and organization_id != tenant_id:
            raise PermissionError("tenant boundary violation")

        return self.repository.list_by_organization(
            organization_id
        )

    def list_by_status(
        self,
        organization_id: UUID,
        status: BusinessAssessmentStatus,
        tenant_id: UUID | None = None,
    ):
        if tenant_id is not None and organization_id != tenant_id:
            raise PermissionError("tenant boundary violation")

        return self.repository.list_by_status(
            organization_id,
            status,
        )

    def exists_by_title(
        self,
        organization_id: UUID,
        title: str,
    ) -> bool:
        return self.repository.exists_by_title(
            organization_id,
            title,
        )
