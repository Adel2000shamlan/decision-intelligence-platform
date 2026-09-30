from uuid import uuid4

import pytest

from app.modules.business_assessment.application.queries import (
    BusinessAssessmentQueryService,
)
from app.modules.business_assessment.domain.models import (
    BusinessAssessment,
    BusinessAssessmentStatus,
)
from app.modules.business_assessment.persistence.sqlite import (
    SQLiteBusinessAssessmentRepository,
)


def make_service():
    return BusinessAssessmentQueryService(
        SQLiteBusinessAssessmentRepository()
    )


def test_get_returns_assessment():
    service = make_service()
    organization_id = uuid4()

    assessment = BusinessAssessment.create(
        organization_id,
        "مشروع استعلام",
    )

    service.repository.save(assessment)

    loaded = service.get(
        assessment.id,
        organization_id,
    )

    assert loaded.id == assessment.id
    assert loaded.organization_id == organization_id


def test_get_rejects_wrong_tenant():
    service = make_service()

    assessment = BusinessAssessment.create(
        uuid4(),
        "مشروع خاص",
    )

    service.repository.save(assessment)

    with pytest.raises(PermissionError):
        service.get(
            assessment.id,
            uuid4(),
        )


def test_list_is_tenant_scoped():
    service = make_service()

    organization_a = uuid4()
    organization_b = uuid4()

    assessment_a = BusinessAssessment.create(
        organization_a,
        "مشروع A",
    )
    assessment_b = BusinessAssessment.create(
        organization_b,
        "مشروع B",
    )

    service.repository.save(assessment_a)
    service.repository.save(assessment_b)

    result = service.list(organization_a, organization_a)

    assert [item.id for item in result] == [
        assessment_a.id
    ]


def test_list_by_status_is_tenant_scoped():
    service = make_service()

    organization_id = uuid4()

    assessment = BusinessAssessment.create(
        organization_id,
        "مشروع حالة",
    )

    service.repository.save(assessment)

    result = service.list_by_status(
        organization_id,
        BusinessAssessmentStatus.DRAFT,
        organization_id,
    )

    assert [item.id for item in result] == [
        assessment.id
    ]


def test_exists_by_title():
    service = make_service()

    organization_id = uuid4()

    assessment = BusinessAssessment.create(
        organization_id,
        "مشروع موجود",
    )

    service.repository.save(assessment)

    assert service.exists_by_title(
        organization_id,
        "مشروع موجود",
    )
