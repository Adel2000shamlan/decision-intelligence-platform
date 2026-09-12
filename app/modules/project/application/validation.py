from uuid import UUID
from app.modules.project.domain.models import Project, ProjectStatus
class ProjectApplicationValidationError(ValueError): pass
class ProjectApplicationValidator:
    @staticmethod
    def validate_create(organization_id,name):
        if not isinstance(organization_id,UUID): raise ProjectApplicationValidationError('organization_id must be UUID')
        if not isinstance(name,str) or not name.strip() or len(name.strip())>200: raise ProjectApplicationValidationError('invalid project name')
    @staticmethod
    def validate_transition(status):
        try: ProjectStatus(status)
        except (ValueError,TypeError) as exc: raise ProjectApplicationValidationError('invalid project status') from exc
    @staticmethod
    def validate_expected_version(v):
        if v is not None and (isinstance(v,bool) or not isinstance(v,int) or v<1): raise ProjectApplicationValidationError('expected_version must be positive integer')
