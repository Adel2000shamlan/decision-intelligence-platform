from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from app.modules.learning.application import LearningFeedbackService
from app.modules.learning.domain.models import (
    LearningObservation,
    LearningOutcomeType,
)
from app.modules.learning.persistence.sqlite import SQLiteLearningRepository


def make_observation(
    tenant_id,
    *,
    metric="revenue",
    outcome=LearningOutcomeType.SUCCESS,
    expected=100.0,
    actual=120.0,
    confidence=0.8,
):
    return LearningObservation.create(
        tenant_id=tenant_id,
        decision_id=uuid4(),
        outcome_type=outcome,
        metric=metric,
        source="test",
        expected_value=expected,
        actual_value=actual,
        confidence=confidence,
        observed_at=datetime.now(timezone.utc),
    )


def test_build_aggregates_learning_feedback():
    tenant_id = uuid4()
    repository = SQLiteLearningRepository()

    first = make_observation(tenant_id)
    second = make_observation(
        tenant_id,
        outcome=LearningOutcomeType.PARTIAL,
        expected=100.0,
        actual=90.0,
        confidence=0.6,
    )
    third = make_observation(
        tenant_id,
        outcome=LearningOutcomeType.FAILURE,
        expected=None,
        actual=None,
        confidence=None,
    )

    repository.save(first)
    repository.save(second)
    repository.save(third)

    feedback = LearningFeedbackService(repository).build(
        tenant_id,
        metric="revenue",
    )

    assert feedback.observation_count == 3
    assert feedback.success_count == 1
    assert feedback.partial_count == 1
    assert feedback.failure_count == 1
    assert feedback.unknown_count == 0
    assert feedback.average_variance == pytest.approx(5.0)
    assert feedback.average_confidence == pytest.approx(0.7)
    assert len(feedback.observations) == 3


def test_feedback_is_tenant_scoped():
    tenant_a = uuid4()
    tenant_b = uuid4()
    repository = SQLiteLearningRepository()

    repository.save(make_observation(tenant_a))
    repository.save(make_observation(tenant_b))

    service = LearningFeedbackService(repository)

    feedback_a = service.build(tenant_a, metric="revenue")
    feedback_b = service.build(tenant_b, metric="revenue")

    assert feedback_a.observation_count == 1
    assert feedback_b.observation_count == 1
    assert feedback_a.observations[0].tenant_id == tenant_a
    assert feedback_b.observations[0].tenant_id == tenant_b


def test_feedback_supports_empty_history():
    tenant_id = uuid4()
    feedback = LearningFeedbackService(
        SQLiteLearningRepository()
    ).build(
        tenant_id,
        metric="new_metric",
    )

    assert feedback.observation_count == 0
    assert feedback.average_variance is None
    assert feedback.average_confidence is None
    assert feedback.latest_observed_at is None
    assert feedback.observations == ()


def test_postgres_feedback_aggregation():
    import os
    import psycopg

    from app.modules.learning.application import LearningFeedbackService
    from app.modules.learning.domain.models import (
        LearningObservation,
        LearningOutcomeType,
    )
    from app.modules.learning.persistence.postgres import (
        PostgresLearningRepository,
    )

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        pytest.skip("DATABASE_URL is not configured")

    tenant_id = uuid4()

    with psycopg.connect(database_url) as connection:
        repository = PostgresLearningRepository(connection)

        try:
            observations = (
                LearningObservation.create(
                    tenant_id=tenant_id,
                    decision_id=uuid4(),
                    outcome_type=LearningOutcomeType.SUCCESS,
                    expected_value=100.0,
                    actual_value=120.0,
                    metric="v113_05_revenue",
                    source="v113_05_test",
                    confidence=0.8,
                ),
                LearningObservation.create(
                    tenant_id=tenant_id,
                    decision_id=uuid4(),
                    outcome_type=LearningOutcomeType.PARTIAL,
                    expected_value=100.0,
                    actual_value=90.0,
                    metric="v113_05_revenue",
                    source="v113_05_test",
                    confidence=0.6,
                ),
                LearningObservation.create(
                    tenant_id=tenant_id,
                    decision_id=uuid4(),
                    outcome_type=LearningOutcomeType.FAILURE,
                    expected_value=None,
                    actual_value=None,
                    metric="v113_05_revenue",
                    source="v113_05_test",
                    confidence=None,
                ),
            )

            for item in observations:
                repository.save(item)

            feedback = LearningFeedbackService(repository).build(
                tenant_id,
                metric="v113_05_revenue",
            )

            assert feedback.observation_count == 3
            assert feedback.success_count == 1
            assert feedback.partial_count == 1
            assert feedback.failure_count == 1
            assert feedback.unknown_count == 0
            assert feedback.average_variance == pytest.approx(5.0)
            assert feedback.average_confidence == pytest.approx(0.7)

        finally:
            with connection.cursor() as cursor:
                cursor.execute(
                    "DELETE FROM learning_observations WHERE tenant_id = %s",
                    (str(tenant_id),),
                )
            connection.commit()


def test_postgres_feedback_is_tenant_scoped():
    import os
    import psycopg

    from app.modules.learning.application import LearningFeedbackService
    from app.modules.learning.domain.models import (
        LearningObservation,
        LearningOutcomeType,
    )
    from app.modules.learning.persistence.postgres import (
        PostgresLearningRepository,
    )

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        pytest.skip("DATABASE_URL is not configured")

    tenant_a = uuid4()
    tenant_b = uuid4()

    with psycopg.connect(database_url) as connection:
        repository = PostgresLearningRepository(connection)

        try:
            repository.save(
                LearningObservation.create(
                    tenant_id=tenant_a,
                    decision_id=uuid4(),
                    outcome_type=LearningOutcomeType.SUCCESS,
                    expected_value=100.0,
                    actual_value=110.0,
                    metric="v113_05_revenue",
                    source="v113_05_test",
                    confidence=0.9,
                )
            )

            repository.save(
                LearningObservation.create(
                    tenant_id=tenant_b,
                    decision_id=uuid4(),
                    outcome_type=LearningOutcomeType.FAILURE,
                    expected_value=100.0,
                    actual_value=50.0,
                    metric="v113_05_revenue",
                    source="v113_05_test",
                    confidence=0.2,
                )
            )

            service = LearningFeedbackService(repository)

            feedback_a = service.build(
                tenant_a,
                metric="v113_05_revenue",
            )
            feedback_b = service.build(
                tenant_b,
                metric="v113_05_revenue",
            )

            assert feedback_a.observation_count == 1
            assert feedback_a.success_count == 1
            assert feedback_a.failure_count == 0

            assert feedback_b.observation_count == 1
            assert feedback_b.success_count == 0
            assert feedback_b.failure_count == 1

        finally:
            with connection.cursor() as cursor:
                cursor.execute(
                    "DELETE FROM learning_observations WHERE tenant_id IN (%s, %s)",
                    (str(tenant_a), str(tenant_b)),
                )
            connection.commit()


def test_postgres_feedback_ignores_missing_variance_and_confidence():
    import os
    import psycopg

    from app.modules.learning.application import LearningFeedbackService
    from app.modules.learning.domain.models import (
        LearningObservation,
        LearningOutcomeType,
    )
    from app.modules.learning.persistence.postgres import (
        PostgresLearningRepository,
    )

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        pytest.skip("DATABASE_URL is not configured")

    tenant_id = uuid4()

    with psycopg.connect(database_url) as connection:
        repository = PostgresLearningRepository(connection)

        try:
            repository.save(
                LearningObservation.create(
                    tenant_id=tenant_id,
                    decision_id=uuid4(),
                    outcome_type=LearningOutcomeType.SUCCESS,
                    expected_value=100.0,
                    actual_value=130.0,
                    metric="v113_05_partial_data",
                    source="v113_05_test",
                    confidence=0.8,
                )
            )

            repository.save(
                LearningObservation.create(
                    tenant_id=tenant_id,
                    decision_id=uuid4(),
                    outcome_type=LearningOutcomeType.UNKNOWN,
                    expected_value=None,
                    actual_value=None,
                    metric="v113_05_partial_data",
                    source="v113_05_test",
                    confidence=None,
                )
            )

            feedback = LearningFeedbackService(repository).build(
                tenant_id,
                metric="v113_05_partial_data",
            )

            assert feedback.observation_count == 2
            assert feedback.success_count == 1
            assert feedback.unknown_count == 1
            assert feedback.average_variance == pytest.approx(30.0)
            assert feedback.average_confidence == pytest.approx(0.8)

        finally:
            with connection.cursor() as cursor:
                cursor.execute(
                    "DELETE FROM learning_observations WHERE tenant_id = %s",
                    (str(tenant_id),),
                )
            connection.commit()


def test_postgres_feedback_empty_metric_history():
    import os
    import psycopg

    from app.modules.learning.application import LearningFeedbackService
    from app.modules.learning.persistence.postgres import (
        PostgresLearningRepository,
    )

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        pytest.skip("DATABASE_URL is not configured")

    tenant_id = uuid4()

    with psycopg.connect(database_url) as connection:
        repository = PostgresLearningRepository(connection)

        feedback = LearningFeedbackService(repository).build(
            tenant_id,
            metric="v113_05_nonexistent_metric",
        )

        assert feedback.observation_count == 0
        assert feedback.average_variance is None
        assert feedback.average_confidence is None
        assert feedback.latest_observed_at is None
        assert feedback.observations == ()
