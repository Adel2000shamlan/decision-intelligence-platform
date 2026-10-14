from uuid import uuid4

from app.modules.learning.application import LearningService
from app.modules.learning.domain.models import LearningOutcomeType
from app.modules.learning.persistence.sqlite import SQLiteLearningRepository


def make_service():
    return LearningService(SQLiteLearningRepository())


def test_observe_persists_and_returns_observation():
    service = make_service()
    tenant_id = uuid4()
    decision_id = uuid4()

    observation = service.observe(
        tenant_id=tenant_id,
        decision_id=decision_id,
        outcome_type=LearningOutcomeType.SUCCESS,
        expected_value=100.0,
        actual_value=120.0,
        metric="revenue",
        source="application_test",
        confidence=0.9,
    )

    assert observation.tenant_id == tenant_id
    assert observation.decision_id == decision_id
    assert observation.variance == 20.0
    assert service.get(
        tenant_id=tenant_id,
        observation_id=observation.id,
    ) == observation


def test_get_is_tenant_scoped():
    service = make_service()
    tenant_a = uuid4()
    tenant_b = uuid4()

    observation = service.observe(
        tenant_id=tenant_a,
        decision_id=uuid4(),
        outcome_type=LearningOutcomeType.PARTIAL,
        metric="customers",
        source="application_test",
    )

    assert service.get(
        tenant_id=tenant_a,
        observation_id=observation.id,
    ) == observation

    assert service.get(
        tenant_id=tenant_b,
        observation_id=observation.id,
    ) is None


def test_list_supports_decision_and_metric_filters():
    service = make_service()
    tenant_id = uuid4()
    decision_id = uuid4()

    first = service.observe(
        tenant_id=tenant_id,
        decision_id=decision_id,
        outcome_type=LearningOutcomeType.SUCCESS,
        metric="revenue",
        source="application_test",
    )

    second = service.observe(
        tenant_id=tenant_id,
        decision_id=decision_id,
        outcome_type=LearningOutcomeType.PARTIAL,
        metric="customers",
        source="application_test",
    )

    assert service.list(
        tenant_id=tenant_id,
        decision_id=decision_id,
    ) == (first, second)

    assert service.list(
        tenant_id=tenant_id,
        metric="revenue",
    ) == (first,)


def test_remove_is_tenant_scoped():
    service = make_service()
    tenant_a = uuid4()
    tenant_b = uuid4()

    observation = service.observe(
        tenant_id=tenant_a,
        decision_id=uuid4(),
        outcome_type=LearningOutcomeType.FAILURE,
        metric="cost",
        source="application_test",
    )

    service.remove(
        tenant_id=tenant_b,
        observation_id=observation.id,
    )

    assert service.get(
        tenant_id=tenant_a,
        observation_id=observation.id,
    ) == observation

    service.remove(
        tenant_id=tenant_a,
        observation_id=observation.id,
    )

    assert service.get(
        tenant_id=tenant_a,
        observation_id=observation.id,
    ) is None
