from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4


@dataclass(frozen=True, slots=True)
class AnalyticsEvent:
    id: UUID
    tenant_id: UUID
    actor_id: UUID | None
    event_name: str
    occurred_at: datetime
    properties: dict[str, str] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        tenant_id: UUID,
        event_name: str,
        actor_id: UUID | None = None,
        properties: dict[str, str] | None = None,
    ) -> "AnalyticsEvent":
        if not event_name.strip():
            raise ValueError("event_name must not be empty")
        return cls(
            id=uuid4(),
            tenant_id=tenant_id,
            actor_id=actor_id,
            event_name=event_name.strip(),
            occurred_at=datetime.now(timezone.utc),
            properties=dict(properties or {}),
        )


@dataclass(frozen=True, slots=True)
class MVPKPI:
    name: str
    description: str
    target: float
    unit: str

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("KPI name must not be empty")
        if self.target < 0:
            raise ValueError("KPI target must be non-negative")


@dataclass(frozen=True, slots=True)
class KPIMeasurement:
    kpi_name: str
    value: float
    measured_at: datetime
    tenant_id: UUID

    @classmethod
    def create(
        cls,
        kpi_name: str,
        value: float,
        tenant_id: UUID,
    ) -> "KPIMeasurement":
        if not kpi_name.strip():
            raise ValueError("KPI name must not be empty")
        return cls(
            kpi_name=kpi_name.strip(),
            value=float(value),
            measured_at=datetime.now(timezone.utc),
            tenant_id=tenant_id,
        )
