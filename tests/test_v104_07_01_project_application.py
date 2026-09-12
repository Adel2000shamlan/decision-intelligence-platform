from uuid import uuid4
import pytest
from app.modules.project.application.service import ProjectApplicationService
from app.modules.project.application.tenant import ProjectTenantGuard
from app.modules.project.in_memory import InMemoryProjectRepository
from app.modules.project.domain.models import ProjectStatus

def test_project_application_create_get_list_and_rename():
    repo=InMemoryProjectRepository(); svc=ProjectApplicationService(repo); org=uuid4()
    p=svc.create(org," Alpha ")
    assert p.name=="Alpha"; assert svc.get(p.id) is p; assert len(svc.list(org))==1
    svc.rename(p.id,"Beta"); assert svc.get(p.id).name=="Beta"

def test_project_application_transition():
    repo=InMemoryProjectRepository(); svc=ProjectApplicationService(repo); p=svc.create(uuid4(),"Alpha")
    svc.transition(p.id, ProjectStatus.ACTIVE); assert p.status is ProjectStatus.ACTIVE

def test_project_application_not_found():
    svc=ProjectApplicationService(InMemoryProjectRepository())
    with pytest.raises(LookupError): svc.rename(uuid4(),"x")

def test_project_tenant_guard():
    repo=InMemoryProjectRepository(); svc=ProjectApplicationService(repo); org=uuid4(); other=uuid4(); p=svc.create(org,"Alpha")
    ProjectTenantGuard.assert_access(p,org)
    with pytest.raises(PermissionError): ProjectTenantGuard.assert_access(p,other)
