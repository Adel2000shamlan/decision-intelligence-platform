from uuid import uuid4

import pytest

from app.modules.business_assessment.domain.models import (
    BusinessAssessment,
    BusinessAssessmentStatus,
)
from app.modules.business_assessment.persistence.sqlite import (
    SQLiteBusinessAssessmentRepository,
)


def make_repository():
    return SQLiteBusinessAssessmentRepository()


def test_save_and_get_by_id():
    repository = make_repository()
    organization_id = uuid4()

    assessment = BusinessAssessment.create(
        organization_id,
        "مشروع تجريبي",
        "وصف المشروع",
    )

    repository.save(assessment)

    loaded = repository.get_by_id(assessment.id)

    assert loaded is not None
    assert loaded.id == assessment.id
    assert loaded.organization_id == organization_id
    assert loaded.title == "مشروع تجريبي"
    assert loaded.idea_description == "وصف المشروع"
    assert loaded.status is BusinessAssessmentStatus.DRAFT
    assert loaded.version == 1


def test_list_by_organization_is_tenant_scoped():
    repository = make_repository()
    organization_a = uuid4()
    organization_b = uuid4()

    assessment_a = BusinessAssessment.create(
        organization_a,
        "مشروع المؤسسة الأولى",
    )
    assessment_b = BusinessAssessment.create(
        organization_b,
        "مشروع المؤسسة الثانية",
    )

    repository.save(assessment_a)
    repository.save(assessment_b)

    result_a = repository.list_by_organization(organization_a)
    result_b = repository.list_by_organization(organization_b)

    assert [item.id for item in result_a] == [assessment_a.id]
    assert [item.id for item in result_b] == [assessment_b.id]


def test_list_by_status_is_tenant_scoped():
    repository = make_repository()
    organization_a = uuid4()
    organization_b = uuid4()

    assessment_a = BusinessAssessment.create(
        organization_a,
        "حالة المؤسسة الأولى",
    )
    assessment_b = BusinessAssessment.create(
        organization_b,
        "حالة المؤسسة الثانية",
    )

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


def test_exists_by_title_is_case_insensitive_within_organization():
    repository = make_repository()
    organization_id = uuid4()

    assessment = BusinessAssessment.create(
        organization_id,
        "مشروع النور",
    )

    repository.save(assessment)

    assert repository.exists_by_title(
        organization_id,
        "  مشروع النور  ",
    )


def test_same_title_is_allowed_in_different_organizations():
    repository = make_repository()

    assessment_a = BusinessAssessment.create(
        uuid4(),
        "مشروع مشترك",
    )
    assessment_b = BusinessAssessment.create(
        uuid4(),
        "مشروع مشترك",
    )

    repository.save(assessment_a)
    repository.save(assessment_b)

    assert repository.get_by_id(assessment_a.id) is not None
    assert repository.get_by_id(assessment_b.id) is not None


def test_duplicate_title_in_same_organization_is_rejected():
    repository = make_repository()
    organization_id = uuid4()

    assessment_a = BusinessAssessment.create(
        organization_id,
        "مشروع مكرر",
    )
    assessment_b = BusinessAssessment.create(
        organization_id,
        "  مشروع مكرر  ",
    )

    repository.save(assessment_a)

    with pytest.raises(Exception):
        repository.save(assessment_b)


def test_version_jump_is_rejected():
    repository = make_repository()
    assessment = BusinessAssessment.create(uuid4(), "قفزة إصدار")

    repository.save(assessment)

    assessment.version = 3

    with pytest.raises(Exception):
        repository.save(assessment)


def test_same_version_same_state_is_idempotent():
    repository = make_repository()
    assessment = BusinessAssessment.create(uuid4(), "Idempotency")

    repository.save(assessment)

    loaded = repository.get_by_id(assessment.id)
    assert loaded is not None

    repository.save(loaded)

    final = repository.get_by_id(assessment.id)

    assert final is not None
    assert final.version == 1
    assert final.title == "Idempotency"


def test_same_version_different_state_is_rejected():
    repository = make_repository()
    assessment = BusinessAssessment.create(uuid4(), "حالة أصلية")

    repository.save(assessment)

    loaded = repository.get_by_id(assessment.id)
    assert loaded is not None

    loaded.title = "حالة مختلفة"

    with pytest.raises(Exception):
        repository.save(loaded)


def test_versioned_update_succeeds():
    repository = make_repository()
    assessment = BusinessAssessment.create(uuid4(), "قبل التحديث")

    repository.save(assessment)

    assessment.update_title("بعد التحديث")
    repository.save(assessment)

    loaded = repository.get_by_id(assessment.id)

    assert loaded is not None
    assert loaded.title == "بعد التحديث"
    assert loaded.version == 2
