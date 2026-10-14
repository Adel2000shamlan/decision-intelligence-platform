from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID, uuid4

from app.shared.domain.errors import InvalidDomainData, BusinessRuleViolation


def _number(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise InvalidDomainData(f"{name} must be numeric")
    return float(value)


@dataclass(frozen=True)
class ForecastObservation:
    tenant_id: UUID
    metric_name: str
    observed_at: datetime
    value: float
    id: UUID

    @classmethod
    def create(cls, tenant_id, metric_name, observed_at, value):
        if not isinstance(tenant_id, UUID):
            raise InvalidDomainData("tenant_id must be UUID")
        if not isinstance(metric_name, str) or not metric_name.strip():
            raise InvalidDomainData("metric_name is required")
        if not isinstance(observed_at, datetime) or observed_at.tzinfo is None:
            raise InvalidDomainData("observed_at must be timezone-aware")
        if observed_at > datetime.now(timezone.utc):
            raise InvalidDomainData("observed_at cannot be in the future")
        return cls(
            tenant_id=tenant_id,
            metric_name=metric_name.strip(),
            observed_at=observed_at,
            value=_number(value, "value"),
            id=uuid4(),
        )


@dataclass(frozen=True)
class ForecastRequest:
    tenant_id: UUID
    metric_name: str
    horizon: int
    minimum_observations: int = 3

    def validate(self):
        if not isinstance(self.tenant_id, UUID):
            raise InvalidDomainData("tenant_id must be UUID")
        if not isinstance(self.metric_name, str) or not self.metric_name.strip():
            raise InvalidDomainData("metric_name is required")
        if isinstance(self.horizon, bool) or not isinstance(self.horizon, int) or self.horizon < 1:
            raise InvalidDomainData("horizon must be integer >= 1")
        if (
            isinstance(self.minimum_observations, bool)
            or not isinstance(self.minimum_observations, int)
            or self.minimum_observations < 2
        ):
            raise InvalidDomainData("minimum_observations must be integer >= 2")


@dataclass(frozen=True)
class ForecastResult:
    tenant_id: UUID
    metric_name: str
    predictions: tuple[float, ...]
    method: str
    observation_count: int
    is_forecast: bool = True


@dataclass(frozen=True)
class SimulationVariable:
    name: str
    value: float
    weight: float = 1.0

    @classmethod
    def create(cls, name, value, weight=1.0):
        if not isinstance(name, str) or not name.strip():
            raise InvalidDomainData("variable name is required")
        value = _number(value, "value")
        weight = _number(weight, "weight")
        if weight < 0:
            raise InvalidDomainData("weight cannot be negative")
        return cls(name.strip(), value, weight)


@dataclass(frozen=True)
class SimulationResult:
    tenant_id: UUID
    scenario_name: str
    baseline: float
    adjusted_value: float
    variables: tuple[SimulationVariable, ...]
    is_estimate: bool = True
