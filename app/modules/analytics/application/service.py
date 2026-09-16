from collections import Counter
from uuid import UUID

from app.modules.analytics.domain.models import AnalyticsEvent, KPIMeasurement, MVPKPI


class AnalyticsService:
    def __init__(self) -> None:
        self._events: list[AnalyticsEvent] = []
        self._measurements: list[KPIMeasurement] = []

    def record(self, event: AnalyticsEvent) -> AnalyticsEvent:
        self._events.append(event)
        return event

    def events(self, tenant_id: UUID) -> tuple[AnalyticsEvent, ...]:
        return tuple(event for event in self._events if event.tenant_id == tenant_id)

    def summary(self, tenant_id: UUID) -> dict[str, int]:
        return dict(Counter(event.event_name for event in self.events(tenant_id)))

    def measure(self, measurement: KPIMeasurement) -> KPIMeasurement:
        self._measurements.append(measurement)
        return measurement

    def measurements(self, tenant_id: UUID) -> tuple[KPIMeasurement, ...]:
        return tuple(
            item for item in self._measurements if item.tenant_id == tenant_id
        )


DEFAULT_MVP_KPIS: tuple[MVPKPI, ...] = (
    MVPKPI(
        "pilot_onboarding_completion_rate",
        "Percentage of pilot participants completing onboarding.",
        0.80,
        "ratio",
    ),
    MVPKPI(
        "weekly_active_pilot_users",
        "Number of distinct pilot users active during a week.",
        10.0,
        "users",
    ),
    MVPKPI(
        "feedback_submission_rate",
        "Percentage of pilot users submitting at least one feedback item.",
        0.50,
        "ratio",
    ),
    MVPKPI(
        "support_first_response_minutes",
        "Target maximum median first-response time for pilot support.",
        60.0,
        "minutes",
    ),
    MVPKPI(
        "critical_incident_rate",
        "Target maximum rate of critical incidents during the pilot.",
        0.05,
        "ratio",
    ),
)
