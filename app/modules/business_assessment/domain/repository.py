from abc import ABC, abstractmethod
from uuid import UUID

from .models import BusinessAssessment, BusinessAssessmentStatus

class BusinessAssessmentRepository(ABC):
    @abstractmethod
    def get_by_id(self, assessment_id: UUID) -> BusinessAssessment | None: ...

    @abstractmethod
    def list_by_organization(self, organization_id: UUID) -> list[BusinessAssessment]: ...

    @abstractmethod
    def list_by_status(self, organization_id: UUID, status: BusinessAssessmentStatus) -> list[BusinessAssessment]: ...

    @abstractmethod
    def exists_by_title(self, organization_id: UUID, title: str) -> bool: ...

    @abstractmethod
    def save(self, assessment: BusinessAssessment, expected_version: int | None = None) -> BusinessAssessment: ...
