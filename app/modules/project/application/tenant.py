from uuid import UUID
from app.modules.project.domain.models import Project
class ProjectTenantGuard:
    @staticmethod
    def assert_access(project: Project, organization_id: UUID) -> None:
        if project.organization_id != organization_id:
            raise PermissionError("project tenant boundary violation")
