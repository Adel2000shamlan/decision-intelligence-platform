import os
from uuid import uuid4

import psycopg
import pytest

from app.shared.domain.errors import BusinessRuleViolation
from app.modules.decision.domain.models import (
    Decision,
    DecisionPriority,
    DecisionStatus,
    DecisionType,
)
from app.modules.decision.persistence.postgres import PostgreSQLDecisionRepository


DATABASE_URL = os.getenv("DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not DATABASE_URL,
    reason="DATABASE_URL is required for PostgreSQL integration test",
)


@pytest.fixture
def repository():
    repo = PostgreSQLDecisionRepository(DATABASE_URL)
    marker = f"V110 PG Decision {uuid4()}"

    yield repo, marker

    with psycopg.connect(DATABASE_URL) as connection:
        connection.execute(
            "DELETE FROM decisions WHERE title LIKE %s",
            (f"{marker}%",),
        )


def make_decision(
    marker,
    *,
    organization_id=None,
    project_id=None,
    title_suffix="",
    description="Persistent decision",
    decision_type=DecisionType.STRATEGIC,
    priority=DecisionPriority.MEDIUM,
):
    return Decision.create(
        organization_id or uuid4(),
        project_id or uuid4(),
        f"{marker} {title_suffix}".strip(),
        description,
        decision_type,
        priority,
    )


def test_postgres_decision_create_and_round_trip(repository):
    repo, marker = repository
    organization_id = uuid4()
    project_id = uuid4()

    decision = make_decision(
        marker,
        organization_id=organization_id,
        project_id=project_id,
        title_suffix="Create",
        description="Stored description",
        decision_type=DecisionType.OPERATIONAL,
        priority=DecisionPriority.HIGH,
    )

    repo.save(decision)
    loaded = repo.get_by_id(decision.id)

    assert loaded is not None
    assert loaded.id == decision.id
    assert loaded.organization_id == organization_id
    assert loaded.project_id == project_id
    assert loaded.title == decision.title
    assert loaded.description == "Stored description"
    assert loaded.decision_type is DecisionType.OPERATIONAL
    assert loaded.priority is DecisionPriority.HIGH
    assert loaded.status is DecisionStatus.DRAFT
    assert loaded.version == 1


def test_postgres_decision_lists_by_project_and_organization(repository):
    repo, marker = repository
    organization_id = uuid4()
    project_a = uuid4()
    project_b = uuid4()

    decision_a1 = make_decision(
        marker,
        organization_id=organization_id,
        project_id=project_a,
        title_suffix="A1",
    )
    decision_a2 = make_decision(
        marker,
        organization_id=organization_id,
        project_id=project_a,
        title_suffix="A2",
    )
    decision_b1 = make_decision(
        marker,
        organization_id=organization_id,
        project_id=project_b,
        title_suffix="B1",
    )

    repo.save(decision_a1)
    repo.save(decision_a2)
    repo.save(decision_b1)

    assert {
        decision.id
        for decision in repo.list_by_project(project_a)
    } >= {decision_a1.id, decision_a2.id}

    assert {
        decision.id
        for decision in repo.list_by_project(project_b)
    } >= {decision_b1.id}

    assert {
        decision.id
        for decision in repo.list_by_organization(organization_id)
    } >= {decision_a1.id, decision_a2.id, decision_b1.id}


def test_postgres_decision_exists_by_title(repository):
    repo, marker = repository
    project_id = uuid4()

    decision = make_decision(
        marker,
        project_id=project_id,
        title_suffix="Exists",
    )

    assert repo.exists_by_title(project_id, decision.title) is False

    repo.save(decision)

    assert repo.exists_by_title(project_id, decision.title) is True
    assert repo.exists_by_title(project_id, decision.title.strip()) is True
    assert repo.exists_by_title(uuid4(), decision.title) is False


def test_postgres_decision_update_persists_version_and_state(repository):
    repo, marker = repository
    decision = make_decision(
        marker,
        title_suffix="Update",
    )

    repo.save(decision)

    decision.start_analysis()
    repo.save(decision)

    loaded = repo.get_by_id(decision.id)

    assert loaded is not None
    assert loaded.status is DecisionStatus.ANALYSIS
    assert loaded.version == 2


def test_postgres_decision_stale_update_is_rejected(repository):
    repo, marker = repository
    decision = make_decision(
        marker,
        title_suffix="Concurrency",
    )

    repo.save(decision)

    first = repo.get_by_id(decision.id)
    stale = repo.get_by_id(decision.id)

    assert first is not None
    assert stale is not None

    first.start_analysis()
    repo.save(first)

    stale.start_analysis()

    with pytest.raises(
        BusinessRuleViolation,
        match="decision concurrency conflict",
    ):
        repo.save(stale)


def test_postgres_decision_duplicate_title_in_same_project_is_rejected(repository):
    repo, marker = repository
    project_id = uuid4()

    first = make_decision(
        marker,
        project_id=project_id,
        title_suffix="Duplicate",
    )
    duplicate = make_decision(
        marker,
        project_id=project_id,
        title_suffix="Duplicate",
    )

    repo.save(first)

    with pytest.raises(
        BusinessRuleViolation,
        match="decision title already exists in project",
    ):
        repo.save(duplicate)


def test_postgres_decision_same_title_is_allowed_in_different_projects(repository):
    repo, marker = repository
    organization_id = uuid4()
    project_a = uuid4()
    project_b = uuid4()

    first = make_decision(
        marker,
        organization_id=organization_id,
        project_id=project_a,
        title_suffix="Same Title",
    )
    second = make_decision(
        marker,
        organization_id=organization_id,
        project_id=project_b,
        title_suffix="Same Title",
    )

    repo.save(first)
    repo.save(second)

    assert repo.get_by_id(first.id) is not None
    assert repo.get_by_id(second.id) is not None
