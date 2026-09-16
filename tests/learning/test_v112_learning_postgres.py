import os
from uuid import uuid4

import psycopg
import pytest

from app.modules.learning.domain.models import (
    LearningObservation,
    LearningOutcomeType,
)
from app.modules.learning.persistence.postgres import PostgresLearningRepository


DATABASE_URL = os.getenv("DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not DATABASE_URL,
    reason="DATABASE_URL is not configured",
)


@pytest.fixture
def repository():
    with psycopg.connect(DATABASE_URL) as connection:
        repo = PostgresLearningRepository(connection)
        yield repo

        with connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM learning_observations"
            )
        connection.commit()


def make_observation(
    tenant_id=None,
    decision_id=None,
    metric="revenue",
    actual_value=120.0,
):
    return LearningObservation.create(
        tenant_id=tenant_id or uuid4(),
        decision_id=decision_id or uuid4(),
        outcome_type=LearningOutcomeType.SUCCESS,
        expected_value=100.0,
        actual_value=actual_value,
        metric=metric,
        source="postgres_test",
        confidence=0.9,
    )


def test_save_and_get(repository):
    tenant_id = uuid4()
    item = make_observation(tenant_id=tenant_id)

    repository.save(item)

    assert repository.get(tenant_id, item.id) == item


def test_get_is_tenant_scoped(repository):
    tenant_a = uuid4()
    tenant_b = uuid4()
    item = make_observation(tenant_id=tenant_a)

    repository.save(item)

    assert repository.get(tenant_a, item.id) == item
    assert repository.get(tenant_b, item.id) is None


def test_list_filters(repository):
    tenant_id = uuid4()
    decision_id = uuid4()

    first = make_observation(
        tenant_id=tenant_id,
        decision_id=decision_id,
        metric="revenue",
    )
    second = make_observation(
        tenant_id=tenant_id,
        decision_id=decision_id,
        metric="customers",
    )

    repository.save(first)
    repository.save(second)

    assert repository.list(
        tenant_id,
        decision_id=decision_id,
    ) == (first, second)

    assert repository.list(
        tenant_id,
        metric="revenue",
    ) == (first,)


def test_upsert(repository):
    tenant_id = uuid4()
    item = make_observation(tenant_id=tenant_id)

    repository.save(item)

    updated = LearningObservation(
        id=item.id,
        tenant_id=item.tenant_id,
        decision_id=item.decision_id,
        outcome_type=LearningOutcomeType.PARTIAL,
        expected_value=item.expected_value,
        actual_value=90.0,
        metric=item.metric,
        source="updated",
        notes="updated",
        observed_at=item.observed_at,
        confidence=0.7,
        created_at=item.created_at,
    )

    repository.save(updated)

    assert repository.get(tenant_id, item.id) == updated


def test_delete_is_tenant_scoped(repository):
    tenant_a = uuid4()
    tenant_b = uuid4()
    item = make_observation(tenant_id=tenant_a)

    repository.save(item)

    repository.delete(tenant_b, item.id)

    assert repository.get(tenant_a, item.id) == item

    repository.delete(tenant_a, item.id)

    assert repository.get(tenant_a, item.id) is None
