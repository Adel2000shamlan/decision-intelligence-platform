from uuid import uuid4

import pytest

from app.modules.authorization.domain.models import Resource, ResourceType
from app.modules.authorization.domain.resource_authorization import ResourceStatus
from app.modules.developer.authorization.resource_resolver import (
    DeveloperResourceResolver,
)
from app.modules.decision.in_memory import InMemoryDecisionRepository
from app.modules.decision.domain.models import Decision
from app.modules.organization.in_memory import InMemoryOrganizationRepository
from app.modules.organization.domain.models import Organization
from app.modules.project.persistence.sqlite import SQLiteProjectRepository


@pytest.fixture
def graph():
    tenant_a = uuid4()
    tenant_b = uuid4()

    org_repo = InMemoryOrganizationRepository()

    org_a = Organization.create("Tenant A Org", "tenant-a")
    org_b = Organization.create("Tenant B Org", "tenant-b")

    org_repo.save(org_a, tenant_a)
    org_repo.save(org_b, tenant_b)

    project_repo = SQLiteProjectRepository()

    from app.modules.project.domain.models import Project

    project_a = Project.create(org_a.id, "Project A")
    project_b = Project.create(org_b.id, "Project B")

    project_repo.save(project_a)
    project_repo.save(project_b)

    decision_repo = InMemoryDecisionRepository()

    decision_a = Decision.create(
        org_a.id,
        project_a.id,
        "Decision A",
    )
    decision_repo.save(decision_a)

    decision_b = Decision.create(
        org_b.id,
        project_b.id,
        "Decision B",
    )
    decision_repo.save(decision_b)

    return {
        "tenant_a": tenant_a,
        "tenant_b": tenant_b,
        "org_a": org_a,
        "org_b": org_b,
        "project_repo": project_repo,
        "decision_repo": decision_repo,
        "project_a": project_a,
        "project_b": project_b,
        "decision_a": decision_a,
        "decision_b": decision_b,
        "org_repo": org_repo,
    }


def resolver(graph):
    return DeveloperResourceResolver(
        organization_repository=graph["org_repo"],
        project_repository=graph["project_repo"],
        decision_repository=graph["decision_repo"],
        risk_repository=object(),
    )


def test_project_resolves_to_real_tenant(graph):
    result = resolver(graph).resolve(
        Resource(
            ResourceType.PROJECT,
            graph["project_a"].id,
            graph["tenant_a"],
        )
    )

    assert result is not None
    assert result.resource.tenant_id == graph["tenant_a"]
    assert result.resource.resource_id == graph["project_a"].id


def test_project_cross_tenant_fails_closed(graph):
    result = resolver(graph).resolve(
        Resource(
            ResourceType.PROJECT,
            graph["project_a"].id,
            graph["tenant_b"],
        )
    )

    assert result is None


def test_tenant_id_is_not_organization_id(graph):
    assert graph["tenant_a"] != graph["org_a"].id

    result = resolver(graph).resolve(
        Resource(
            ResourceType.PROJECT,
            graph["project_a"].id,
            graph["tenant_a"],
        )
    )

    assert result is not None


def test_decision_resolves_through_organization(graph):
    result = resolver(graph).resolve(
        Resource(
            ResourceType.DECISION,
            graph["decision_a"].id,
            graph["tenant_a"],
        )
    )

    assert result is not None
    assert result.resource.tenant_id == graph["tenant_a"]


def test_decision_cross_tenant_fails_closed(graph):
    result = resolver(graph).resolve(
        Resource(
            ResourceType.DECISION,
            graph["decision_a"].id,
            graph["tenant_b"],
        )
    )

    assert result is None


def test_missing_organization_tenant_fails_closed(graph):
    orphan_org = Organization.create("Orphan", "orphan")
    graph["org_repo"].save(orphan_org)

    from app.modules.project.domain.models import Project

    orphan_project = Project.create(
        orphan_org.id,
        "Orphan Project",
    )
    graph["project_repo"].save(orphan_project)

    result = resolver(graph).resolve(
        Resource(
            ResourceType.PROJECT,
            orphan_project.id,
            graph["tenant_a"],
        )
    )

    assert result is None


def test_missing_project_fails_closed(graph):
    result = resolver(graph).resolve(
        Resource(
            ResourceType.PROJECT,
            uuid4(),
            graph["tenant_a"],
        )
    )

    assert result is None


def test_unsupported_resource_fails_closed(graph):
    result = resolver(graph).resolve(
        Resource(
            ResourceType.OPTION,
            uuid4(),
            graph["tenant_a"],
        )
    )

    assert result is None


def test_risk_resolves_through_project_organization_tenant(graph):
    from app.modules.risk.in_memory import InMemoryRiskRepository
    from app.modules.risk.domain.models import Risk

    risk_repository = InMemoryRiskRepository()
    risk = Risk.create(
        graph["project_a"].id,
        "Risk A",
    )
    risk_repository.save(risk)

    result = DeveloperResourceResolver(
        organization_repository=graph["org_repo"],
        project_repository=graph["project_repo"],
        decision_repository=graph["decision_repo"],
        risk_repository=risk_repository,
    ).resolve(
        Resource(
            ResourceType.RISK,
            risk.id,
            graph["tenant_a"],
        )
    )

    assert result is not None
    assert result.resource.resource_type is ResourceType.RISK
    assert result.resource.resource_id == risk.id
    assert result.resource.tenant_id == graph["tenant_a"]
    assert result.status is ResourceStatus.ACTIVE


def test_risk_cross_tenant_fails_closed(graph):
    from app.modules.risk.in_memory import InMemoryRiskRepository
    from app.modules.risk.domain.models import Risk

    risk_repository = InMemoryRiskRepository()
    risk = Risk.create(
        graph["project_a"].id,
        "Risk A",
    )
    risk_repository.save(risk)

    result = DeveloperResourceResolver(
        organization_repository=graph["org_repo"],
        project_repository=graph["project_repo"],
        decision_repository=graph["decision_repo"],
        risk_repository=risk_repository,
    ).resolve(
        Resource(
            ResourceType.RISK,
            risk.id,
            graph["tenant_b"],
        )
    )

    assert result is None


def test_risk_missing_project_fails_closed(graph):
    from app.modules.risk.in_memory import InMemoryRiskRepository
    from app.modules.risk.domain.models import Risk

    risk_repository = InMemoryRiskRepository()
    risk = Risk.create(
        uuid4(),
        "Orphan Risk",
    )
    risk_repository.save(risk)

    result = DeveloperResourceResolver(
        organization_repository=graph["org_repo"],
        project_repository=graph["project_repo"],
        decision_repository=graph["decision_repo"],
        risk_repository=risk_repository,
    ).resolve(
        Resource(
            ResourceType.RISK,
            risk.id,
            graph["tenant_a"],
        )
    )

    assert result is None


def test_archived_risk_resolves_as_archived(graph):
    from app.modules.risk.in_memory import InMemoryRiskRepository
    from app.modules.risk.domain.models import Risk, RiskStatus

    risk_repository = InMemoryRiskRepository()
    risk = Risk.create(
        graph["project_a"].id,
        "Archived Risk",
    )
    risk.identify()
    risk.assess(2, 2)
    risk.accept()
    risk.close()
    risk.archive()
    risk_repository.save(risk)

    result = DeveloperResourceResolver(
        organization_repository=graph["org_repo"],
        project_repository=graph["project_repo"],
        decision_repository=graph["decision_repo"],
        risk_repository=risk_repository,
    ).resolve(
        Resource(
            ResourceType.RISK,
            risk.id,
            graph["tenant_a"],
        )
    )

    assert result is not None
    assert result.status is ResourceStatus.ARCHIVED
    assert risk.status is RiskStatus.ARCHIVED
