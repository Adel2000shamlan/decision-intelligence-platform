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

    commands = BusinessAssessmentCommandHandler(repository)
    queries = BusinessAssessmentQueryService(repository)
    authorization = BusinessAssessmentAuthorizationAdapter()

    return BusinessAssessmentApplicationFacade(
        commands=commands,
        queries=queries,
        authorization=authorization,
    )


def test_create_through_facade():
    facade = make_facade()
    organization_id = uuid4()
    actor_id = uuid4()

    assessment = facade.create(
        organization_id=organization_id,
        title="مشروع عبر الواجهة",
        idea_description="اختبار طبقة التطبيق",
        actor_id=actor_id,
        tenant_id=organization_id,
    )

    assert assessment.organization_id == organization_id
    assert assessment.title == "مشروع عبر الواجهة"
    assert assessment.status is BusinessAssessmentStatus.DRAFT
    assert assessment.version == 1


def test_get_is_tenant_scoped():
    facade = make_facade()
    organization_id = uuid4()
    actor_id = uuid4()

    assessment = facade.create(
        organization_id=organization_id,
        title="مشروع معزول",
        actor_id=actor_id,
        tenant_id=organization_id,
    )

    loaded = facade.get(
        assessment.id,
        organization_id,
    )

    assert loaded.id == assessment.id

    with pytest.raises(PermissionError):
        facade.get(
            assessment.id,
            uuid4(),
        )


def test_start_data_collection_uses_expected_version():
    facade = make_facade()
    organization_id = uuid4()
    actor_id = uuid4()

    assessment = facade.create(
        organization_id=organization_id,
        title="مشروع جمع البيانات",
        actor_id=actor_id,
        tenant_id=organization_id,
    )

    updated = facade.start_data_collection(
        assessment.id,
        actor_id=actor_id,
        tenant_id=organization_id,
        expected_version=1,
    )

    assert updated.status is BusinessAssessmentStatus.DATA_COLLECTION
    assert updated.version == 2


def test_wrong_expected_version_is_rejected():
    facade = make_facade()
    organization_id = uuid4()
    actor_id = uuid4()

    assessment = facade.create(
        organization_id=organization_id,
        title="اختبار التعارض",
        actor_id=actor_id,
        tenant_id=organization_id,
    )

    with pytest.raises(Exception):
        facade.start_data_collection(
            assessment.id,
            actor_id=actor_id,
            tenant_id=organization_id,
            expected_version=99,
        )


def test_update_title_through_facade():
    facade = make_facade()
    organization_id = uuid4()
    actor_id = uuid4()

    assessment = facade.create(
        organization_id=organization_id,
        title="قبل التعديل",
        actor_id=actor_id,
        tenant_id=organization_id,
    )

    updated = facade.update_title(
        assessment.id,
        "بعد التعديل",
        actor_id=actor_id,
        tenant_id=organization_id,
        expected_version=1,
    )

    assert updated.title == "بعد التعديل"
    assert updated.version == 2
