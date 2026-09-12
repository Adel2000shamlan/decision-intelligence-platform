from uuid import uuid4
from app.modules.organization.persistence.sqlite import SQLiteOrganizationRepository
from app.modules.organization.application.service import OrganizationApplicationService
from app.modules.organization.application.events import InMemoryOrganizationEventPublisher, OrganizationAuditSink
from app.modules.organization.application.validation import OrganizationApplicationValidator
from app.modules.organization.domain.models import Organization
from app.modules.project.application.implementation import ProjectApplicationService

def test_organization_persistence_application_and_query():
 r=SQLiteOrganizationRepository(); p=OrganizationApplicationService(r); o=p.create('Acme','acme'); assert p.get(o.id).slug=='acme'; assert len(p.list())==1

def test_events_audit_validation():
 OrganizationApplicationValidator.validate('A','a'); pub=InMemoryOrganizationEventPublisher(); sink=OrganizationAuditSink(); o=Organization.create('A','a'); e=o.pull_events()[0]; pub.publish(e); pub.publish(e); sink.record(o.id,uuid4(),'create',o.version); assert len(pub.events)==1 and len(sink.records)==1

def test_generic_implementation_services():
 s=ProjectApplicationService(); x=s.create({'name':'p'}); assert s.get(x['id'])==x and len(s.list())==1
