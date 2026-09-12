from uuid import UUID
import inspect
import app.modules.organization.domain.models as domain_models
from app.modules.organization.domain.models import Organization, OrganizationStatus, OrganizationCreated, OrganizationRenamed, OrganizationSlugChanged
from app.modules.organization.in_memory import InMemoryOrganizationRepository, DefaultOrganizationFactory
from app.modules.organization.application.commands import *
from app.modules.organization.application.ports import OrganizationUnitOfWork
from app.shared.domain.errors import InvalidDomainData, InvalidStateTransition, BusinessRuleViolation, EntityNotFound


def uow():
    repo=InMemoryOrganizationRepository()
    return repo, OrganizationUnitOfWork(repo, DefaultOrganizationFactory(), lambda: None)

def test_create_and_event():
    o=Organization.create(' Acme ', 'Acme-Co')
    assert isinstance(o.id, UUID); assert o.name=='Acme'; assert o.slug=='acme-co'; assert o.status==OrganizationStatus.ACTIVE; assert o.version==1
    assert isinstance(o.pull_events()[0], OrganizationCreated)

def test_validation():
    for kwargs in ({'name':'','slug':'x'},{'name':'   ','slug':'x'},{'name':'x','slug':''},{'name':'x','slug':'a b'},{'name':'x','slug':'a/b'}):
        try: Organization(**kwargs)
        except InvalidDomainData: pass
        else: assert False

def test_lifecycle_and_version():
    o=Organization.create('A','a'); v=o.version; o.suspend(); assert o.status==OrganizationStatus.SUSPENDED and o.version==v+1
    o.reactivate(); assert o.status==OrganizationStatus.ACTIVE
    o.archive(); assert o.status==OrganizationStatus.ARCHIVED
    before=o.version
    for fn in (o.reactivate,o.suspend,o.archive):
        try: fn()
        except InvalidStateTransition: pass
        else: assert False
    assert o.version==before and o.status==OrganizationStatus.ARCHIVED

def test_real_mutation_only():
    o=Organization.create('A','a'); v=o.version; o.rename('A'); o.change_slug('a'); assert o.version==v
    o.rename('B'); assert o.version==v+1; o.change_slug('b'); assert o.version==v+2
    assert isinstance(o.pull_events()[1], OrganizationRenamed)

def test_commands_and_unique_slug():
    repo,u=uow(); h=OrganizationCommandHandler(u)
    a=h.create(CreateOrganization('A','a')); assert a.version==1
    try: h.create(CreateOrganization('B','a'))
    except BusinessRuleViolation: pass
    else: assert False
    h.rename(RenameOrganization(a.id,'A2')); h.change_slug(ChangeOrganizationSlug(a.id,'a2')); h.suspend(SuspendOrganization(a.id)); h.reactivate(ReactivateOrganization(a.id)); h.archive(ArchiveOrganization(a.id))
    assert repo.get_by_id(a.id).status==OrganizationStatus.ARCHIVED

def test_not_found():
    repo,u=uow(); h=OrganizationCommandHandler(u)
    from uuid import uuid4
    try: h.archive(ArchiveOrganization(uuid4()))
    except EntityNotFound: pass
    else: assert False

def test_repository_contract_has_no_infrastructure_imports():
    source=inspect.getsource(domain_models)
    assert not any(x in source for x in ('fastapi','sqlalchemy','postgres','redis'))
