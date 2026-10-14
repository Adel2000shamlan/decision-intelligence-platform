import os
from uuid import uuid4

import psycopg
import pytest

from app.modules.business_assessment.domain.models import (
    BusinessAssessment,
    BusinessAssessmentStatus,
)
from app.modules.business_assessment.persistence.postgres import (
    PostgreSQLBusinessAssessmentRepository,
)


DSN = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres@localhost:5432/decision_intelligence",
)


@pytest.fixture
def repository():
    repository = PostgreSQLBusinessAssessmentRepository(DSN)
    yield repository


@pytest.fixture
def cleanup_ids():
    ids = []

    yield ids

    if ids:
        with psycopg.connect(DSN) as connection:
            connection.execute(
                "DELETE FROM business_assessments WHERE id = ANY(%s)",
                ([str(item) for item in ids],),
            )
            connection.commit()


def test_save_and_get_by_id(repository, cleanup_ids):
    organization_id = uuid4()
    assessment = BusinessAssessment.create(
        organization_id,
        "PostgreSQL Smoke",
        "اختبار PostgreSQL",
    )
    cleanup_ids.append(assessment.id)

    repository.save(assessment)

    loaded = repository.get_by_id(assessment.id)

    assert loaded is not None
    assert loaded.id == assessment.id
    assert loaded.organization_id == organization_id
    assert loaded.title == "PostgreSQL Smoke"
    assert loaded.version == 1


def test_list_by_status_is_tenant_scoped(repository, cleanup_ids):
    organization_a = uuid4()
    organization_b = uuid4()

    assessment_a = BusinessAssessment.create(
        organization_a,
        "Tenant A",
    )
    assessment_b = BusinessAssessment.create(
        organization_b,
        "Tenant B",
    )

    cleanup_ids.extend([assessment_a.id, assessment_b.id])

    repository.save(assessment_a)
    repository.save(assessment_b)

    result_a = repository.list_by_status(
        organization_a,
        BusinessAssessmentStatus.DRAFT,
    )
    result_b = repository.list_by_status(
        organization_b,
        BusinessAssessmentStatus.DRAFT,
    )

    assert [item.id for item in result_a] == [assessment_a.id]
    assert [item.id for item in result_b] == [assessment_b.id]


def test_duplicate_title_is_scoped_to_organization(
    repository,
    cleanup_ids,
):
    organization_a = uuid4()
    organization_b = uuid4()

    assessment_a = BusinessAssessment.create(
        organization_a,
        "مشروع مشترك",
    )
    assessment_b = BusinessAssessment.create(
        organization_b,
        "مشروع مشترك",
    )

    cleanup_ids.extend([assessment_a.id, assessment_b.id])

    repository.save(assessment_a)
    repository.save(assessment_b)

    assert repository.exists_by_title(
        organization_a,
        "مشروع مشترك",
    )
    assert repository.exists_by_title(
        organization_b,
        "مشروع مشترك",
    )


def test_duplicate_title_in_same_organization_is_rejected(
    repository,
    cleanup_ids,
):
    organization_id = uuid4()

    first = BusinessAssessment.create(
        organization_id,
        "عنوان مكرر",
    )
    second = BusinessAssessment.create(
        organization_id,
        "  عنوان مكرر  ",
    )

    cleanup_ids.append(first.id)

    repository.save(first)

    with pytest.raises(Exception):
        repository.save(second)


def test_same_version_same_state_is_idempotent(
    repository,
    cleanup_ids,
):
    assessment = BusinessAssessment.create(
        uuid4(),
        "Idempotent PostgreSQL",
    )
    cleanup_ids.append(assessment.id)

    repository.save(assessment)

    loaded = repository.get_by_id(assessment.id)
    assert loaded is not None

    repository.save(loaded)

    final = repository.get_by_id(assessment.id)

    assert final is not None
    assert final.version == 1
    assert final.title == "Idempotent PostgreSQL"


def test_same_version_different_state_is_rejected(
    repository,
    cleanup_ids,
):
    assessment = BusinessAssessment.create(
        uuid4(),
        "Original PostgreSQL",
    )
    cleanup_ids.append(assessment.id)

    repository.save(assessment)

    loaded = repository.get_by_id(assessment.id)
    assert loaded is not None

    loaded.title = "Changed PostgreSQL"

    with pytest.raises(Exception):
        repository.save(loaded)


def test_version_jump_is_rejected(repository, cleanup_ids):
    assessment = BusinessAssessment.create(
        uuid4(),
        "Version Jump PostgreSQL",
    )
    cleanup_ids.append(assessment.id)

    repository.save(assessment)

    assessment.version = 3

    with pytest.raises(Exception):
        repository.save(assessment)


def test_versioned_update_succeeds(repository, cleanup_ids):
    assessment = BusinessAssessment.create(
        uuid4(),
        "Before PostgreSQL",
    )
    cleanup_ids.append(assessment.id)

    repository.save(assessment)

    assessment.update_title("After PostgreSQL")
    repository.save(assessment)

    loaded = repository.get_by_id(assessment.id)

    assert loaded is not None
    assert loaded.title == "After PostgreSQL"
    assert loaded.version == 2
