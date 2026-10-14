from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from app.modules.learning.domain.models import (
    LearningObservation,
    LearningOutcomeType,
)
from app.shared.domain.errors import BusinessRuleViolation


def make_observation(**overrides):
    values = {
        "tenant_id": uuid4(),
        "decision_id": uuid4(),
        "outcome_type": LearningOutcomeType.SUCCESS,
        "metric": "revenue",
        "source": "monthly_report",
        "expected_value": 100.0,
        "actual_value": 120.0,
        "confidence": 0.9,
    }
    values.update(overrides)
    return LearningObservation.create(**values)


def test_create_observation():
    item = make_observation()

    assert item.id
    assert item.outcome_type is LearningOutcomeType.SUCCESS
    assert item.expected_value == 100.0
    assert item.actual_value == 120.0
    assert item.variance == 20.0
    assert item.confidence == 0.9
    assert item.created_at.tzinfo is not None


def test_outcome_type_string_is_coerced():
    item = make_observation(outcome_type="partial")

    assert item.outcome_type is LearningOutcomeType.PARTIAL


def test_variance_is_none_without_both_values():
    assert make_observation(actual_value=None).variance is None
    assert make_observation(expected_value=None).variance is None


def test_rejects_empty_metric():
    with pytest.raises(BusinessRuleViolation):
        make_observation(metric="   ")


def test_rejects_empty_source():
    with pytest.raises(BusinessRuleViolation):
        make_observation(source="   ")


def test_rejects_invalid_confidence():
    with pytest.raises(BusinessRuleViolation):
        make_observation(confidence=-0.1)

    with pytest.raises(BusinessRuleViolation):
        make_observation(confidence=1.1)

    with pytest.raises(BusinessRuleViolation):
        make_observation(confidence=True)


def test_rejects_boolean_numeric_values():
    with pytest.raises(BusinessRuleViolation):
        make_observation(expected_value=True)

    with pytest.raises(BusinessRuleViolation):
        make_observation(actual_value=False)


def test_rejects_naive_observed_at():
    with pytest.raises(BusinessRuleViolation):
        make_observation(observed_at=datetime.now())


def test_accepts_timezone_aware_observed_at():
    observed_at = datetime.now(timezone.utc) - timedelta(days=1)
    item = make_observation(observed_at=observed_at)

    assert item.observed_at == observed_at
