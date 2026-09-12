import inspect
from uuid import UUID, uuid4

from app.modules.organization.domain.models import Organization
from app.modules.organization.in_memory import InMemoryOrganizationRepository
from app.modules.project.domain.models import (
    Project, ProjectStatus, ProjectCreated, ProjectActivated, ProjectCompleted,
    ProjectArchived, ProjectCancelled, ProjectRenamed,
)
from app.modules.project.domain.services import ProjectPolicyService
from app.modules.project.in_memory import InMemoryProjectRepository, DefaultProjectFactory
from app.modules.project.application.commands import *
from app.modules.project.application.ports import ProjectUnitOfWork
from app.shared.domain.errors import InvalidDomainData, InvalidStateTransition, BusinessRuleViolation, EntityNotFound


def make_uow():
    org_repo = InMemoryOrganizationRepository()
    project_repo = InMemoryProjectRepository()
    org = Organization.create("Acme", "acme")
    org_repo.save(org)
    return org, org_repo, project_repo, ProjectUnitOfWork(project_repo, org_repo, DefaultProjectFactory(), ProjectPolicyService(), lambda: None)


def test_project_entity_and_creation_event():
    org_id = uuid4()
    p = Project.create(org_id, " Demo ")
    assert isinstance(p.id, UUID)
    assert p.organization_id == org_id
    assert p.name == "Demo"
    assert p.status is ProjectStatus.DRAFT
    assert p.version == 1
    assert isinstance(p.pull_events()[0], ProjectCreated)


def test_structural_validation():
    for name in ("", "   ", None, 123):
        try:
            Project(uuid4(), name)
        except InvalidDomainData:
            pass
        else:
            assert False
    try:
        Project("not-a-uuid", "Demo")
    except InvalidDomainData:
        pass
    else:
        assert False


def test_complete_lifecycle_and_versioning():
    p = Project.create(uuid4(), "Demo")
    assert p.status is ProjectStatus.DRAFT
    p.activate(); assert p.status is ProjectStatus.ACTIVE and p.version == 2
    p.complete(); assert p.status is ProjectStatus.COMPLETED and p.version == 3
    p.archive(); assert p.status is ProjectStatus.ARCHIVED and p.version == 4
    before = (p.version, p.status)
    for fn in (p.activate, p.complete, p.archive, p.cancel):
        try: fn()
        except InvalidStateTransition: pass
        else: assert False
    assert (p.version, p.status) == before


def test_draft_can_cancel_and_cancelled_can_archive():
    p = Project.create(uuid4(), "Demo")
    p.cancel(); assert p.status is ProjectStatus.CANCELLED
    p.archive(); assert p.status is ProjectStatus.ARCHIVED


def test_real_mutation_only_and_events():
    p = Project.create(uuid4(), "A")
    v = p.version
    p.rename("A")
    assert p.version == v
    p.rename("B")
    assert p.version == v + 1
    events = p.pull_events()
    assert isinstance(events[0], ProjectCreated)
    assert isinstance(events[1], ProjectRenamed)
    p.activate(); p.complete(); p.archive()
    events = p.pull_events()
    assert isinstance(events[0], ProjectActivated)
    assert isinstance(events[1], ProjectCompleted)
    assert isinstance(events[2], ProjectArchived)


def test_commands_and_project_name_uniqueness():
    org, org_repo, repo, uow = make_uow()
    handler = ProjectCommandHandler(uow)
    p = handler.create(CreateProject(org.id, "P1"))
    assert p.version == 1
    try:
        handler.create(CreateProject(org.id, "P1"))
    except BusinessRuleViolation:
        pass
    else:
        assert False
    handler.rename(RenameProject(p.id, "P2"))
    handler.activate(ActivateProject(p.id))
    handler.complete(CompleteProject(p.id))
    handler.archive(ArchiveProject(p.id))
    assert repo.get_by_id(p.id).status is ProjectStatus.ARCHIVED


def test_create_requires_active_organization():
    org, org_repo, repo, uow = make_uow()
    org.suspend(); org_repo.save(org)
    handler = ProjectCommandHandler(uow)
    try:
        handler.create(CreateProject(org.id, "P1"))
    except BusinessRuleViolation:
        pass
    else:
        assert False


def test_not_found():
    _, _, _, uow = make_uow()
    handler = ProjectCommandHandler(uow)
    try:
        handler.archive(ArchiveProject(uuid4()))
    except EntityNotFound:
        pass
    else:
        assert False


def test_domain_boundary_has_no_infrastructure_imports():
    files = [
        __import__('app.modules.project.domain.models', fromlist=['x']),
        __import__('app.modules.project.domain.repository', fromlist=['x']),
        __import__('app.modules.project.domain.services', fromlist=['x']),
    ]
    for module in files:
        source = inspect.getsource(module)
        assert not any(x in source.lower() for x in ('fastapi', 'sqlalchemy', 'postgres', 'redis', 'http'))
