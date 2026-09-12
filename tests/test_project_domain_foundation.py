from uuid import uuid4
from app.modules.project.domain.models import Project, ProjectStatus
from app.shared.domain.errors import InvalidStateTransition

def test_project_foundation_lifecycle():
    p=Project(uuid4(),'Demo'); assert p.status==ProjectStatus.DRAFT
    p.transition(ProjectStatus.ACTIVE); p.transition(ProjectStatus.COMPLETED); p.transition(ProjectStatus.ARCHIVED)
    assert p.status==ProjectStatus.ARCHIVED
    try: p.transition(ProjectStatus.ACTIVE)
    except InvalidStateTransition: pass
    else: assert False
