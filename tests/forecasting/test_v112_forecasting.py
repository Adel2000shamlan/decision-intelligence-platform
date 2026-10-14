from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from app.modules.forecasting import ForecastingService
from app.modules.forecasting.domain import (
    ForecastObservation,
    ForecastRequest,
    SimulationVariable,
)
from app.shared.domain.errors import BusinessRuleViolation, InvalidDomainData


def test_forecast_requires_sufficient_time_series_data():
    tenant_id = uuid4()
    service = ForecastingService()

    service.record_observation(
        ForecastObservation.create(
            tenant_id,
            "revenue",
            datetime.now(timezone.utc) - timedelta(days=1),
            100,
        )
    )

    with pytest.raises(BusinessRuleViolation, match="insufficient observations"):
        service.forecast(ForecastRequest(tenant_id, "revenue", 2))


def test_forecast_uses_deterministic_rolling_mean_baseline():
    tenant_id = uuid4()
    service = ForecastingService()
    now = datetime.now(timezone.utc)

    for index, value in enumerate((100, 120, 140, 160)):
        service.record_observation(
            ForecastObservation.create(
                tenant_id,
                "revenue",
                now - timedelta(days=4 - index),
                value,
            )
        )

    result = service.forecast(ForecastRequest(tenant_id, "revenue", 3))

    assert result.method == "rolling_mean_baseline"
    assert result.observation_count == 4
    assert result.predictions == (140.0, 140.0, 140.0)
    assert result.is_forecast is True


def test_forecast_is_tenant_isolated():
    tenant_a = uuid4()
    tenant_b = uuid4()
    service = ForecastingService()
    now = datetime.now(timezone.utc)

    for value in (10, 20, 30):
        service.record_observation(
            ForecastObservation.create(
                tenant_a, "revenue", now - timedelta(minutes=value), value
            )
        )

    for value in (100, 200, 300):
        service.record_observation(
            ForecastObservation.create(
                tenant_b, "revenue", now - timedelta(minutes=value), value
            )
        )

    result = service.forecast(ForecastRequest(tenant_a, "revenue", 1))
    assert result.predictions == (20.0,)
    assert result.observation_count == 3


def test_future_observation_is_rejected():
    with pytest.raises(InvalidDomainData, match="future"):
        ForecastObservation.create(
            uuid4(),
            "revenue",
            datetime.now(timezone.utc) + timedelta(days=1),
            100,
        )


def test_simulation_is_explicitly_an_estimate():
    tenant_id = uuid4()
    variables = (
        SimulationVariable.create("demand_change", 20, 2),
        SimulationVariable.create("price_effect", -10, 1),
    )

    result = ForecastingService().simulate(
        tenant_id,
        "base_case",
        100,
        variables,
    )

    assert result.adjusted_value == pytest.approx(110.0)
    assert result.is_estimate is True


def test_simulation_requires_variables():
    with pytest.raises(BusinessRuleViolation, match="at least one variable"):
        ForecastingService().simulate(uuid4(), "base_case", 100, ())

def test_observation_rejects_non_numeric_and_boolean_values():
    tenant_id = uuid4()
    observed_at = datetime.now(timezone.utc)
    with pytest.raises(InvalidDomainData):
        ForecastObservation.create(tenant_id, "revenue", observed_at, True)
    with pytest.raises(InvalidDomainData):
        ForecastObservation.create(tenant_id, "revenue", observed_at, "100")


def test_forecast_request_requires_at_least_two_observations():
    request = ForecastRequest(uuid4(), "revenue", 1, minimum_observations=1)
    with pytest.raises(InvalidDomainData):
        request.validate()


def test_simulation_rejects_invalid_tenant_and_scenario():
    service = ForecastingService()
    with pytest.raises(InvalidDomainData):
        service.simulate("not-a-uuid", "base", 100, (SimulationVariable.create("growth", 10),))
    with pytest.raises(InvalidDomainData):
        service.simulate(uuid4(), " ", 100, (SimulationVariable.create("growth", 10),))


def test_simulation_rejects_boolean_baseline():
    service = ForecastingService()
    with pytest.raises((InvalidDomainData, ValueError, TypeError)):
        service.simulate(uuid4(), "base", True, (SimulationVariable.create("growth", 10),))

def test_duplicate_observation_timestamp_is_rejected():
    tenant_id = uuid4()
    observed_at = datetime.now(timezone.utc)
    service = ForecastingService()

    observation = ForecastObservation.create(
        tenant_id, "revenue", observed_at, 100
    )
    service.record_observation(observation)

    duplicate = ForecastObservation.create(
        tenant_id, "revenue", observed_at, 120
    )

    with pytest.raises(
        BusinessRuleViolation,
        match="duplicate observation",
    ):
        service.record_observation(duplicate)


def test_same_timestamp_for_different_metrics_is_allowed():
    tenant_id = uuid4()
    observed_at = datetime.now(timezone.utc)
    service = ForecastingService()

    service.record_observation(
        ForecastObservation.create(
            tenant_id, "revenue", observed_at, 100
        )
    )
    service.record_observation(
        ForecastObservation.create(
            tenant_id, "customers", observed_at, 20
        )
    )

    assert len(service.observations(tenant_id, "revenue")) == 1
    assert len(service.observations(tenant_id, "customers")) == 1


def test_same_metric_and_timestamp_across_tenants_is_allowed():
    tenant_a = uuid4()
    tenant_b = uuid4()
    observed_at = datetime.now(timezone.utc)
    service = ForecastingService()

    service.record_observation(
        ForecastObservation.create(
            tenant_a, "revenue", observed_at, 100
        )
    )
    service.record_observation(
        ForecastObservation.create(
            tenant_b, "revenue", observed_at, 200
        )
    )

    assert service.observations(tenant_a, "revenue")[0].value == 100.0
    assert service.observations(tenant_b, "revenue")[0].value == 200.0
