import os
from uuid import uuid4

import psycopg
import pytest

from app.shared.domain.errors import BusinessRuleViolation
from app.modules.risk.domain.models import (
    Risk,
    RiskLevel,
    RiskSource,
    RiskStatus,
)
from app.modules.risk.persistence.postgres import PostgreSQLRiskRepository


DATABASE_URL = os.getenv("DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not DATABASE_URL,
    reason="DATABASE_URL is required for PostgreSQL integration test",
)


@pytest.fixture
def repository():
    repo = PostgreSQLRiskRepository(DATABASE_URL)
    marker = f"V110 PG Risk {uuid4()}"

    yield repo, marker

    with psycopg.connect(DATABASE_URL) as connection:
        connection.execute(
            "DELETE FROM risks WHERE title LIKE %s",
            (f"{marker}%",),
        )


def make_risk(
    marker,
    *,
    project_id=None,
    decision_id=None,
    title_suffix="",
    description="Persistent risk",
    source=RiskSource.HUMAN,
):
    return Risk.create(
        project_id or uuid4(),
        f"{marker} {title_suffix}".strip(),
        description,
        decision_id,
        source,
    )


def make_assessed_risk(
    marker,
    *,
    project_id=None,
    decision_id=None,
    title_suffix="Assessed",
):
    risk = make_risk(
        marker,
        project_id=project_id,
        decision_id=decision_id,
        title_suffix=title_suffix,
        description="Assessed persistent risk",
        source=RiskSource.AI,
    )
    risk.identify()
    risk.assess(4, 4)
    risk.start_mitigation()
    risk.monitor(2, 2)
    return risk


def test_postgres_risk_create_and_round_trip(repository):
    repo, marker = repository
    project_id = uuid4()
    decision_id = uuid4()

    risk = make_risk(
        marker,
        project_id=project_id,
        decision_id=decision_id,
        title_suffix="Create",
        description="Stored description",
        source=RiskSource.AI,
    )

    repo.save(risk)
    loaded = repo.get_by_id(risk.id)

    assert loaded is not None
    assert loaded.id == risk.id
    assert loaded.project_id == project_id
    assert loaded.decision_id == decision_id
    assert loaded.title == risk.title
    assert loaded.description == "Stored description"
    assert loaded.source is RiskSource.AI
    assert loaded.status is RiskStatus.DRAFT
    assert loaded.probability is None
    assert loaded.impact is None
    assert loaded.score is None
    assert loaded.level is None
    assert loaded.residual_probability is None
    assert loaded.residual_impact is None
    assert loaded.residual_score is None
    assert loaded.residual_level is None
    assert loaded.version == 1


def test_postgres_risk_assessment_and_residual_round_trip(repository):
    repo, marker = repository
    project_id = uuid4()
    decision_id = uuid4()

    risk = make_risk(
        marker,
        project_id=project_id,
        decision_id=decision_id,
        title_suffix="Assessed",
        description="Assessed persistent risk",
        source=RiskSource.AI,
    )

    repo.save(risk)

    risk.identify()
    repo.save(risk)
    risk.assess(4, 4)
    repo.save(risk)
    risk.start_mitigation()
    repo.save(risk)
    risk.monitor(2, 2)
    repo.save(risk)

    loaded = repo.get_by_id(risk.id)

    assert loaded is not None
    assert loaded.status is RiskStatus.MONITORED
    assert loaded.probability == 4
    assert loaded.impact == 4
    assert loaded.score == 16
    assert loaded.level is RiskLevel.HIGH
    assert loaded.residual_probability == 2
    assert loaded.residual_impact == 2
    assert loaded.residual_score == 4
    assert loaded.residual_level is RiskLevel.LOW
    assert loaded.version == 5


def test_postgres_risk_lists_by_project_and_decision(repository):
    repo, marker = repository
    project_a = uuid4()
    project_b = uuid4()
    decision_a = uuid4()
    decision_b = uuid4()

    risk_a1 = make_risk(
        marker,
        project_id=project_a,
        decision_id=decision_a,
        title_suffix="A1",
    )
    risk_a2 = make_risk(
        marker,
        project_id=project_a,
        decision_id=decision_a,
        title_suffix="A2",
    )
    risk_b1 = make_risk(
        marker,
        project_id=project_b,
        decision_id=decision_b,
        title_suffix="B1",
    )

    repo.save(risk_a1)
    repo.save(risk_a2)
    repo.save(risk_b1)

    assert {
        risk.id
        for risk in repo.list_by_project(project_a)
    } >= {risk_a1.id, risk_a2.id}

    assert {
        risk.id
        for risk in repo.list_by_project(project_b)
    } >= {risk_b1.id}

    assert {
        risk.id
        for risk in repo.list_by_decision(decision_a)
    } >= {risk_a1.id, risk_a2.id}

    assert {
        risk.id
        for risk in repo.list_by_decision(decision_b)
    } >= {risk_b1.id}


def test_postgres_risk_exists_by_title(repository):
    repo, marker = repository
    project_id = uuid4()

    risk = make_risk(
        marker,
        project_id=project_id,
        title_suffix="Exists",
    )

    assert repo.exists_by_title(project_id, risk.title) is False

    repo.save(risk)

    assert repo.exists_by_title(project_id, risk.title) is True
    assert repo.exists_by_title(project_id, risk.title.strip()) is True
    assert repo.exists_by_title(uuid4(), risk.title) is False


def test_postgres_risk_update_persists_version_and_state(repository):
    repo, marker = repository
    risk = make_risk(
        marker,
        title_suffix="Update",
    )

    repo.save(risk)

    risk.identify()
    repo.save(risk)

    risk.assess(3, 3)
    repo.save(risk)

    loaded = repo.get_by_id(risk.id)

    assert loaded is not None
    assert loaded.status is RiskStatus.ASSESSED
    assert loaded.probability == 3
    assert loaded.impact == 3
    assert loaded.score == 9
    assert loaded.level is RiskLevel.MEDIUM
    assert loaded.version == 3


def test_postgres_risk_stale_update_is_rejected(repository):
    repo, marker = repository
    risk = make_risk(
        marker,
        title_suffix="Concurrency",
    )

    repo.save(risk)

    first = repo.get_by_id(risk.id)
    stale = repo.get_by_id(risk.id)

    assert first is not None
    assert stale is not None

    first.identify()
    repo.save(first)

    stale.identify()

    with pytest.raises(
        BusinessRuleViolation,
        match="risk concurrency conflict",
    ):
        repo.save(stale)


def test_postgres_risk_duplicate_title_in_same_project_is_rejected(repository):
    repo, marker = repository
    project_id = uuid4()

    first = make_risk(
        marker,
        project_id=project_id,
        title_suffix="Duplicate",
    )
    duplicate = make_risk(
        marker,
        project_id=project_id,
        title_suffix="Duplicate",
    )

    repo.save(first)

    with pytest.raises(
        BusinessRuleViolation,
        match="risk title already exists in project",
    ):
        repo.save(duplicate)


def test_postgres_risk_same_title_is_allowed_in_different_projects(repository):
    repo, marker = repository
    project_a = uuid4()
    project_b = uuid4()

    first = make_risk(
        marker,
        project_id=project_a,
        title_suffix="Same Title",
    )
    second = make_risk(
        marker,
        project_id=project_b,
        title_suffix="Same Title",
    )

    repo.save(first)
    repo.save(second)

    assert repo.get_by_id(first.id) is not None
    assert repo.get_by_id(second.id) is not None
