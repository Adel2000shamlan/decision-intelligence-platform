from uuid import uuid4

import pytest

from app.modules.business_assessment.application.authorization import (
    BusinessAssessmentAuthorizationAdapter,
)
from app.modules.business_assessment.application.commands import (
    BusinessAssessmentCommandHandler,
)
from app.modules.business_assessment.application.queries import (
    BusinessAssessmentQueryService,
)
from app.modules.business_assessment.application.service import (
    BusinessAssessmentApplicationFacade,
)
from app.modules.business_assessment.domain.models import (
    BusinessAssessmentStatus,
)
from app.modules.business_assessment.persistence.sqlite import (
    SQLiteBusinessAssessmentRepository,
)


def make_facade():
    repository = SQLiteBusinessAssessmentRepository()

    return BusinessAssessmentApplicationFacade(
        commands=BusinessAssessmentCommandHandler(repository),
        queries=BusinessAssessmentQueryService(repository),
        authorization=BusinessAssessmentAuthorizationAdapter(),
    )


def create_assessment(facade):
    organization_id = uuid4()
    actor_id = uuid4()

    assessment = facade.create(
        organization_id=organization_id,
        title="اختبار دورة الحياة",
        actor_id=actor_id,
        tenant_id=organization_id,
    )

    return assessment, organization_id, actor_id


def test_full_lifecycle():
    facade = make_facade()

    assessment, organization_id, actor_id = create_assessment(
        facade
    )

    assessment = facade.start_data_collection(
        assessment.id,
        actor_id=actor_id,
        tenant_id=organization_id,
        expected_version=1,
    )

    assert assessment.status is BusinessAssessmentStatus.DATA_COLLECTION
    assert assessment.version == 2

    assessment = facade.start_analysis(
        assessment.id,
        actor_id=actor_id,
        tenant_id=organization_id,
        expected_version=2,
    )

    assert assessment.status is BusinessAssessmentStatus.UNDER_ANALYSIS
    assert assessment.version == 3

    assessment = facade.return_to_data_collection(
        assessment.id,
        actor_id=actor_id,
        tenant_id=organization_id,
        expected_version=3,
    )

    assert assessment.status is BusinessAssessmentStatus.DATA_COLLECTION
    assert assessment.version == 4

    assessment = facade.start_analysis(
        assessment.id,
        actor_id=actor_id,
        tenant_id=organization_id,
        expected_version=4,
    )

    assert assessment.status is BusinessAssessmentStatus.UNDER_ANALYSIS
    assert assessment.version == 5

    assessment = facade.complete(
        assessment.id,
        actor_id=actor_id,
        tenant_id=organization_id,
        expected_version=5,
    )

    assert assessment.status is BusinessAssessmentStatus.COMPLETED
    assert assessment.version == 6

    assessment = facade.archive(
        assessment.id,
        actor_id=actor_id,
        tenant_id=organization_id,
        expected_version=6,
    )

    assert assessment.status is BusinessAssessmentStatus.ARCHIVED
    assert assessment.version == 7


def test_wrong_tenant_cannot_change_state():
    facade = make_facade()

    assessment, organization_id, actor_id = create_assessment(
        facade
    )

    with pytest.raises(PermissionError):
        facade.start_data_collection(
            assessment.id,
            actor_id=actor_id,
            tenant_id=uuid4(),
            expected_version=1,
        )

    loaded = facade.get(
        assessment.id,
        organization_id,
    )

    assert loaded.status is BusinessAssessmentStatus.DRAFT
    assert loaded.version == 1


def test_stale_version_is_rejected():
    facade = make_facade()

    assessment, organization_id, actor_id = create_assessment(
        facade
    )

    facade.start_data_collection(
        assessment.id,
        actor_id=actor_id,
        tenant_id=organization_id,
        expected_version=1,
    )

    with pytest.raises(Exception):
        facade.start_analysis(
            assessment.id,
            actor_id=actor_id,
            tenant_id=organization_id,
            expected_version=1,
        )
