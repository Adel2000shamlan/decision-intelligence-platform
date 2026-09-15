from uuid import uuid4

import pytest

from app.modules.decision.application.commands import (
    ApproveDecision,
    CloseDecision,
    CreateDecision,
    ExecuteDecision,
    StartDecisionAnalysis,
    SubmitDecisionForApproval,
)
from app.modules.decision.application.commands import DecisionCommandHandler
from app.modules.decision.application.ports import DecisionUnitOfWork
from app.modules.decision.domain.models import DecisionStatus
from app.modules.decision.domain.services import DecisionDomainService, DecisionPolicyService
from app.modules.decision.in_memory import (
    DefaultDecisionFactory,
    InMemoryDecisionRepository,
)


@pytest.fixture
def handler():
    repository = InMemoryDecisionRepository()
    uow = DecisionUnitOfWork(
        repository=repository,
        factory=DefaultDecisionFactory(),
        policy=DecisionPolicyService(),
    )
    return DecisionCommandHandler(uow)


def test_application_decision_full_lifecycle(handler):
    organization_id = uuid4()
    project_id = uuid4()
    actor_id = uuid4()

    decision = handler.create(
        CreateDecision(
            organization_id=organization_id,
            project_id=project_id,
            title="Application Decision",
            actor_id=actor_id,
        )
    )

    assert decision.status is DecisionStatus.DRAFT
    assert decision.version == 1

    handler.start_analysis(
        StartDecisionAnalysis(decision.id, actor_id)
    )

    handler.submit_for_approval(
        SubmitDecisionForApproval(decision.id, actor_id)
    )

    with pytest.raises(Exception):
        handler.approve(ApproveDecision(decision.id))

    handler.approve(
        ApproveDecision(decision.id, actor_id)
    )
    assert decision.status is DecisionStatus.APPROVED

    handler.execute(
        ExecuteDecision(decision.id, actor_id)
    )

    handler.close(
        CloseDecision(decision.id, actor_id)
    )

    assert decision.status is DecisionStatus.CLOSED
    assert decision.version == 6


def test_application_requires_human_actor_for_approval(handler):
    decision = handler.create(
        CreateDecision(
            organization_id=uuid4(),
            project_id=uuid4(),
            title="Human Approval Gate",
        )
    )

    handler.start_analysis(
        StartDecisionAnalysis(decision.id)
    )
    handler.submit_for_approval(
        SubmitDecisionForApproval(decision.id)
    )

    with pytest.raises(Exception, match="human actor approval is required"):
        handler.approve(
            ApproveDecision(decision.id)
        )


def test_domain_supports_optimistic_concurrency():
    repository = InMemoryDecisionRepository()
    service = DecisionDomainService()

    decision = service.create(
        repository,
        uuid4(),
        uuid4(),
        "Concurrency Decision",
    ).entity

    service.start_analysis(
        repository,
        decision.id,
        expected_version=1,
    )

    with pytest.raises(Exception, match="aggregate version conflict"):
        service.submit_for_approval(
            repository,
            decision.id,
            expected_version=1,
        )
