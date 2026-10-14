import os
from datetime import datetime, timezone
from uuid import uuid4

import psycopg
import pytest

from app.modules.intelligence.integration.learning_bridge import (
    DecisionLearningBridge,
)
from app.modules.learning.application import LearningService
from app.modules.learning.domain.models import LearningOutcomeType
from app.modules.learning.persistence.postgres import (
    PostgresLearningRepository,
)
from app.modules.decision.domain.models import (
    DecisionOutcomeRecorded,
)
from app.shared.domain.events import (
    DomainEventEnvelope,
    EventMetadata,
)

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
            cursor.execute("DELETE FROM learning_observations")
        connection.commit()


def make_outcome_event(tenant_id, decision_id, event_id=None):
    now = datetime.now(timezone.utc)

    payload = DecisionOutcomeRecorded(
        event_id=event_id or uuid4(),
        occurred_at=now,
        aggregate_id=decision_id,
        actor_id=uuid4(),
        outcome_type="success",
        metric="revenue",
        expected_value=100.0,
        actual_value=125.0,
        notes="Observed after execution",
        confidence=0.95,
    )

    return DomainEventEnvelope(
        event_id=payload.event_id,
        event_type="DecisionOutcomeRecorded",
        occurred_at=now,
        aggregate_id=decision_id,
        aggregate_type="Decision",
        aggregate_version=5,
        payload=payload,
        metadata=EventMetadata(
            correlation_id=uuid4(),
            actor_id=payload.actor_id,
            tenant_id=tenant_id,
        ),
    )


def test_outcome_event_is_durable_idempotent_across_new_bridge(
    repository,
):
    tenant_id = uuid4()
    decision_id = uuid4()
    event = make_outcome_event(tenant_id, decision_id)

    DecisionLearningBridge(
        LearningService(repository)
    ).handle(event)

    first = repository.list(
        tenant_id,
        decision_id=decision_id,
    )

    DecisionLearningBridge(
        LearningService(repository)
    ).handle(event)

    second = repository.list(
        tenant_id,
        decision_id=decision_id,
    )

    assert len(first) == 1
    assert len(second) == 1
    assert second[0] == first[0]
    assert second[0].source_event_id == event.event_id
    assert second[0].metric == "revenue"
    assert second[0].expected_value == 100.0
    assert second[0].actual_value == 125.0
    assert second[0].confidence == 0.95
    assert second[0].outcome_type is LearningOutcomeType.SUCCESS


def test_same_source_event_id_is_isolated_by_tenant(repository):
    tenant_a = uuid4()
    tenant_b = uuid4()
    decision_a = uuid4()
    decision_b = uuid4()
    event_id = uuid4()

    event_a = make_outcome_event(
        tenant_a,
        decision_a,
        event_id=event_id,
    )
    event_b = make_outcome_event(
        tenant_b,
        decision_b,
        event_id=event_id,
    )

    DecisionLearningBridge(
        LearningService(repository)
    ).handle(event_a)

    DecisionLearningBridge(
        LearningService(repository)
    ).handle(event_b)

    observations_a = repository.list(
        tenant_a,
        decision_id=decision_a,
    )
    observations_b = repository.list(
        tenant_b,
        decision_id=decision_b,
    )

    assert len(observations_a) == 1
    assert len(observations_b) == 1
    assert observations_a[0].source_event_id == event_id
    assert observations_b[0].source_event_id == event_id
    assert observations_a[0].tenant_id == tenant_a
    assert observations_b[0].tenant_id == tenant_b


def test_source_event_lookup_is_tenant_scoped(repository):
    tenant_a = uuid4()
    tenant_b = uuid4()
    decision_id = uuid4()
    event_id = uuid4()

    event = make_outcome_event(
        tenant_a,
        decision_id,
        event_id=event_id,
    )

    DecisionLearningBridge(
        LearningService(repository)
    ).handle(event)

    assert (
        repository.get_by_source_event_id(
            tenant_a,
            event_id,
        )
        is not None
    )

    assert (
        repository.get_by_source_event_id(
            tenant_b,
            event_id,
        )
        is None
    )
