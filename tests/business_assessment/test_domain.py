from uuid import uuid4

import pytest

from app.modules.business_assessment.domain.models import (
    BusinessAssessment,
    BusinessAssessmentCreated,
    BusinessAssessmentCompleted,
    BusinessAssessmentDataCollectionStarted,
    BusinessAssessmentAnalysisStarted,
    BusinessAssessmentArchived,
    BusinessAssessmentUpdated,
    BusinessAssessmentStatus,
)
from app.shared.domain.errors import InvalidDomainData


def test_create_emits_created_event():
    organization_id = uuid4()

    assessment = BusinessAssessment.create(
        organization_id,
        "فكرة مشروع",
        "وصف المشروع",
    )

    assert assessment.organization_id == organization_id
    assert assessment.title == "فكرة مشروع"
    assert assessment.idea_description == "وصف المشروع"
    assert assessment.status is BusinessAssessmentStatus.DRAFT
    assert assessment.version == 1

    events = assessment.pull_events()

    assert len(events) == 1
    assert isinstance(events[0], BusinessAssessmentCreated)
    assert events[0].aggregate_id == assessment.id


def test_state_transitions_increment_version_and_emit_events():
    assessment = BusinessAssessment.create(uuid4(), "اختبار")

    assessment.pull_events()

    assessment.start_data_collection()
    assert assessment.status is BusinessAssessmentStatus.DATA_COLLECTION
    assert assessment.version == 2
    assert isinstance(
        assessment.pull_events()[0],
        BusinessAssessmentDataCollectionStarted,
    )

    assessment.start_analysis()
    assert assessment.status is BusinessAssessmentStatus.UNDER_ANALYSIS
    assert assessment.version == 3
    assert isinstance(
        assessment.pull_events()[0],
        BusinessAssessmentAnalysisStarted,
    )

    assessment.complete()
    assert assessment.status is BusinessAssessmentStatus.COMPLETED
    assert assessment.version == 4
    assert isinstance(
        assessment.pull_events()[0],
        BusinessAssessmentCompleted,
    )

    assessment.archive()
    assert assessment.status is BusinessAssessmentStatus.ARCHIVED
    assert assessment.version == 5
    assert isinstance(
        assessment.pull_events()[0],
        BusinessAssessmentArchived,
    )


def test_invalid_transition_is_rejected():
    assessment = BusinessAssessment.create(uuid4(), "اختبار")
    assessment.pull_events()

    with pytest.raises(Exception):
        assessment.complete()


def test_archived_is_terminal():
    assessment = BusinessAssessment.create(uuid4(), "اختبار")
    assessment.pull_events()

    assessment.archive()

    with pytest.raises(Exception):
        assessment.start_data_collection()


def test_update_title_increments_version_and_emits_event():
    assessment = BusinessAssessment.create(uuid4(), "العنوان القديم")
    assessment.pull_events()

    assessment.update_title("العنوان الجديد")

    assert assessment.title == "العنوان الجديد"
    assert assessment.version == 2

    events = assessment.pull_events()

    assert len(events) == 1
    assert isinstance(events[0], BusinessAssessmentUpdated)
    assert events[0].old_title == "العنوان القديم"
    assert events[0].new_title == "العنوان الجديد"


def test_same_title_does_not_change_version():
    assessment = BusinessAssessment.create(uuid4(), "نفس العنوان")
    assessment.pull_events()

    assessment.update_title("نفس العنوان")

    assert assessment.version == 1
    assert assessment.pull_events() == ()


@pytest.mark.parametrize(
    "title",
    ["", "   "],
)
def test_title_is_required(title):
    with pytest.raises(InvalidDomainData):
        BusinessAssessment.create(uuid4(), title)


def test_title_is_trimmed():
    assessment = BusinessAssessment.create(uuid4(), "  مشروع تجريبي  ")

    assert assessment.title == "مشروع تجريبي"


def test_invariants_reject_invalid_updated_timestamp():
    assessment = BusinessAssessment.create(uuid4(), "اختبار")

    assessment.updated_at = assessment.created_at.replace(
        year=assessment.created_at.year - 1
    )

    with pytest.raises(InvalidDomainData):
        assessment.validate_invariants()
