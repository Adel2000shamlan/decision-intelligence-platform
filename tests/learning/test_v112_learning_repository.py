from uuid import uuid4

from app.modules.learning.domain.models import (
    LearningObservation,
    LearningOutcomeType,
)
from app.modules.learning.persistence.sqlite import SQLiteLearningRepository


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
        source="test",
        confidence=0.9,
    )


def test_save_and_get():
    repository = SQLiteLearningRepository()
    tenant_id = uuid4()
    item = make_observation(tenant_id=tenant_id)

    repository.save(item)

    assert repository.get(tenant_id, item.id) == item


def test_get_is_tenant_scoped():
    repository = SQLiteLearningRepository()
    tenant_a = uuid4()
    tenant_b = uuid4()
    item = make_observation(tenant_id=tenant_a)

    repository.save(item)

    assert repository.get(tenant_a, item.id) == item
    assert repository.get(tenant_b, item.id) is None


def test_list_is_tenant_scoped():
    repository = SQLiteLearningRepository()
    tenant_a = uuid4()
    tenant_b = uuid4()

    first = make_observation(tenant_id=tenant_a)
    second = make_observation(tenant_id=tenant_b)

    repository.save(first)
    repository.save(second)

    assert repository.list(tenant_a) == (first,)
    assert repository.list(tenant_b) == (second,)


def test_list_filters_by_decision_and_metric():
    repository = SQLiteLearningRepository()
    tenant_id = uuid4()
    decision_a = uuid4()
    decision_b = uuid4()

    first = make_observation(
        tenant_id=tenant_id,
        decision_id=decision_a,
        metric="revenue",
    )
    second = make_observation(
        tenant_id=tenant_id,
        decision_id=decision_a,
        metric="customers",
    )
    third = make_observation(
        tenant_id=tenant_id,
        decision_id=decision_b,
        metric="revenue",
    )

    for item in (first, second, third):
        repository.save(item)

    assert repository.list(tenant_id, decision_id=decision_a) == (first, second)
    assert repository.list(tenant_id, metric="revenue") == (first, third)
    assert repository.list(
        tenant_id,
        decision_id=decision_a,
        metric="customers",
    ) == (second,)


def test_save_upserts_same_id():
    repository = SQLiteLearningRepository()
    tenant_id = uuid4()
    item = make_observation(tenant_id=tenant_id, actual_value=120.0)

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
        notes="updated observation",
        observed_at=item.observed_at,
        confidence=0.7,
        created_at=item.created_at,
    )

    repository.save(updated)

    assert repository.get(tenant_id, item.id) == updated
    assert repository.list(tenant_id) == (updated,)


def test_delete_is_tenant_scoped():
    repository = SQLiteLearningRepository()
    tenant_a = uuid4()
    tenant_b = uuid4()
    item = make_observation(tenant_id=tenant_a)

    repository.save(item)

    repository.delete(tenant_b, item.id)
    assert repository.get(tenant_a, item.id) == item

    repository.delete(tenant_a, item.id)
    assert repository.get(tenant_a, item.id) is None


def test_list_orders_by_creation_time_and_id():
    repository = SQLiteLearningRepository()
    tenant_id = uuid4()

    first = make_observation(tenant_id=tenant_id)
    second = make_observation(tenant_id=tenant_id)

    repository.save(second)
    repository.save(first)

    items = repository.list(tenant_id)

    assert {items[0].id, items[1].id} == {first.id, second.id}
    assert [item.created_at for item in items] == sorted(
        item.created_at for item in items
    )
