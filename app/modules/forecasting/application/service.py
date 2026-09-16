from collections import defaultdict
from statistics import mean
from uuid import UUID

from app.shared.domain.errors import InvalidDomainData, BusinessRuleViolation
from ..domain.models import (
    ForecastObservation,
    ForecastRequest,
    ForecastResult,
    SimulationResult,
    SimulationVariable,
)


class ForecastingService:
    def __init__(self):
        self._observations: dict[UUID, list[ForecastObservation]] = defaultdict(list)

    def record_observation(self, observation: ForecastObservation) -> ForecastObservation:
        if not isinstance(observation, ForecastObservation):
            raise InvalidDomainData("observation must be ForecastObservation")

        existing = self._observations.get(observation.tenant_id, ())
        for item in existing:
            if (
                item.metric_name == observation.metric_name
                and item.observed_at == observation.observed_at
            ):
                raise BusinessRuleViolation(
                    "duplicate observation for metric and timestamp"
                )

        self._observations[observation.tenant_id].append(observation)
        return observation

    def observations(self, tenant_id: UUID, metric_name: str) -> tuple[ForecastObservation, ...]:
        return tuple(
            sorted(
                (
                    item
                    for item in self._observations.get(tenant_id, [])
                    if item.metric_name == metric_name
                ),
                key=lambda item: item.observed_at,
            )
        )

    def forecast(self, request: ForecastRequest) -> ForecastResult:
        request.validate()
        observations = self.observations(request.tenant_id, request.metric_name)

        if len(observations) < request.minimum_observations:
            raise BusinessRuleViolation(
                f"insufficient observations: required {request.minimum_observations}, "
                f"received {len(observations)}"
            )

        values = [item.value for item in observations]
        baseline = mean(values[-3:])
        predictions = tuple(float(baseline) for _ in range(request.horizon))

        return ForecastResult(
            tenant_id=request.tenant_id,
            metric_name=request.metric_name,
            predictions=predictions,
            method="rolling_mean_baseline",
            observation_count=len(observations),
        )

    def simulate(
        self,
        tenant_id: UUID,
        scenario_name: str,
        baseline: float,
        variables: tuple[SimulationVariable, ...],
    ) -> SimulationResult:
        if not isinstance(tenant_id, UUID):
            raise InvalidDomainData("tenant_id must be UUID")
        if not isinstance(scenario_name, str) or not scenario_name.strip():
            raise InvalidDomainData("scenario_name is required")
        if isinstance(baseline, bool) or not isinstance(baseline, (int, float)):
            raise InvalidDomainData("baseline must be numeric")
        baseline = float(baseline)

        if not variables:
            raise BusinessRuleViolation("simulation requires at least one variable")

        total_weight = sum(item.weight for item in variables)
        if total_weight <= 0:
            raise BusinessRuleViolation("simulation weights must have positive total")

        adjustment = sum(item.value * item.weight for item in variables) / total_weight

        return SimulationResult(
            tenant_id=tenant_id,
            scenario_name=scenario_name.strip(),
            baseline=baseline,
            adjusted_value=baseline + adjustment,
            variables=variables,
        )
